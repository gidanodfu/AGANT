# AGANT — Detección híbrida de fraude financiero (reglas + ML + grafo + Laya).
# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Entrena el modelo online (RF o GBM), elige el umbral y lo congela en disco.

El modelo servido se selecciona con ``AGANT_MODEL_KIND`` (``rf`` o ``gbm``;
por defecto ``gbm``, que supera al RF en F1 y PR-AUC con la misma latencia
de orden). El umbral se elige por F1 en VALIDATION y se guarda en el
artefacto, de modo que el servicio lo respeta sin valores mágicos.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

from ..config import Settings
from ..contracts.transaction import MODEL_FEATURE_NAMES
from ..data.temporal_split import SplitName, TemporalSplit
from ..features import load_meta, read_artifacts
from .metrics import binary_metrics
from .thresholds import DEFAULT_THRESHOLDS, select_threshold

MODEL_FILENAME = "online_model.joblib"

RF_PARAMS: dict = {
    "n_estimators": 20,
    "max_depth": 20,
    "min_samples_leaf": 2,
    "max_features": "sqrt",
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1,
}

GBM_PARAMS: dict = {
    "max_iter": 200,
    "learning_rate": 0.1,
    "class_weight": "balanced",
    "random_state": 42,
}

MODEL_KINDS = ("rf", "gbm")


def build_model(kind: str):
    """Construye el estimador servido por nombre (cualquiera con ``predict_proba``)."""
    if kind == "rf":
        return RandomForestClassifier(**RF_PARAMS)
    if kind == "gbm":
        return HistGradientBoostingClassifier(**GBM_PARAMS)
    raise ValueError(f"modelo desconocido: {kind!r}; usar {MODEL_KINDS}")


def split_mask(steps: np.ndarray, split: SplitName, temporal: TemporalSplit | None = None) -> np.ndarray:
    temporal = temporal or TemporalSplit()
    low, high = temporal.bounds(split)
    mask = np.ones(steps.shape[0], dtype=bool)
    if low is not None:
        mask &= steps >= low
    if high is not None:
        mask &= steps <= high
    return mask


def train_online(settings: Settings, *, kind: str | None = None) -> dict:
    kind = (kind or settings.model_kind).strip().lower()
    if kind not in MODEL_KINDS:
        raise ValueError(f"AGANT_MODEL_KIND inválido: {kind!r}; usar {MODEL_KINDS}")

    artifacts = read_artifacts(settings)
    meta = load_meta(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()

    train_mask = split_mask(steps, SplitName.TRAIN)
    val_mask = split_mask(steps, SplitName.VALIDATION)

    x_train = np.asarray(features[train_mask], dtype=np.float32)
    y_train = np.asarray(labels[train_mask], dtype=np.int8)
    x_val = np.asarray(features[val_mask], dtype=np.float32)
    y_val = np.asarray(labels[val_mask], dtype=np.int8)

    model = build_model(kind)
    t0 = time.time()
    model.fit(x_train, y_train)
    train_seconds = time.time() - t0
    # Inferencia en el servicio con n_jobs=1 (evita overhead por fila).
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1

    # El umbral se elige en VALIDATION y viaja con el artefacto.
    val_scores = model.predict_proba(x_val)[:, 1]
    selected = select_threshold(y_val, val_scores, "f1", DEFAULT_THRESHOLDS)
    threshold = float(selected["best"]["threshold"])
    metrics = binary_metrics(y_val, val_scores, threshold)
    params = RF_PARAMS if kind == "rf" else GBM_PARAMS

    model_version = f"{kind}_online_{meta['feature_version']}_{time.strftime('%Y%m%d%H%M%S')}"
    settings.models_path.mkdir(parents=True, exist_ok=True)
    model_path = settings.models_path / MODEL_FILENAME
    joblib.dump(
        {
            "model": model,
            "feature_names": list(MODEL_FEATURE_NAMES),
            "feature_version": meta["feature_version"],
            "model_version": model_version,
            "model_kind": kind,
            "threshold": threshold,
            "params": params,
        },
        model_path,
    )

    payload = {
        "model": type(model).__name__,
        "model_kind": kind,
        "model_version": model_version,
        "feature_version": meta["feature_version"],
        "dataset": "paysim",
        "split": "validation",
        "threshold": threshold,
        "n_features": len(MODEL_FEATURE_NAMES),
        "feature_names": list(MODEL_FEATURE_NAMES),
        "params": params,
        "train_seconds": train_seconds,
        "metrics": metrics,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / "model_validation.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def load_model(settings: Settings, path: Path | None = None) -> dict:
    model_path = path or (settings.models_path / MODEL_FILENAME)
    return joblib.load(model_path)

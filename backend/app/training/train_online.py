# Copyright (C) 2026 Josue David (gidanodfu)
# https://github.com/gidanodfu/AGANT
#
# This file is part of AGANT.
#
# AGANT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# AGANT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with AGANT. If not, see <https://www.gnu.org/licenses/>.

"""Entrena el Random Forest online (15 features) y lo congela en disco."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from ..config import Settings
from ..contracts.transaction import MODEL_FEATURE_NAMES
from ..data.temporal_split import SplitName, TemporalSplit
from ..features import load_meta, read_artifacts
from .metrics import binary_metrics

MODEL_FILENAME = "random_forest_online.joblib"
THRESHOLD = 0.5

RF_PARAMS: dict = {
    "n_estimators": 20,
    "max_depth": 20,
    "min_samples_leaf": 2,
    "max_features": "sqrt",
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1,
}


def split_mask(steps: np.ndarray, split: SplitName, temporal: TemporalSplit | None = None) -> np.ndarray:
    temporal = temporal or TemporalSplit()
    low, high = temporal.bounds(split)
    mask = np.ones(steps.shape[0], dtype=bool)
    if low is not None:
        mask &= steps >= low
    if high is not None:
        mask &= steps <= high
    return mask


def train_online(settings: Settings) -> dict:
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

    model = RandomForestClassifier(**RF_PARAMS)
    t0 = time.time()
    model.fit(x_train, y_train)
    train_seconds = time.time() - t0

    scores = model.predict_proba(x_val)[:, 1]
    metrics = binary_metrics(y_val, scores, THRESHOLD)

    model_version = f"rf_online_{meta['feature_version']}_{time.strftime('%Y%m%d%H%M%S')}"
    settings.models_path.mkdir(parents=True, exist_ok=True)
    model_path = settings.models_path / MODEL_FILENAME
    joblib.dump(
        {
            "model": model,
            "feature_names": list(MODEL_FEATURE_NAMES),
            "feature_version": meta["feature_version"],
            "model_version": model_version,
            "threshold": THRESHOLD,
            "rf_params": RF_PARAMS,
        },
        model_path,
    )

    payload = {
        "model": "RandomForestClassifier",
        "model_version": model_version,
        "feature_version": meta["feature_version"],
        "dataset": "paysim",
        "split": "validation",
        "threshold": THRESHOLD,
        "n_features": len(MODEL_FEATURE_NAMES),
        "feature_names": list(MODEL_FEATURE_NAMES),
        "rf_params": RF_PARAMS,
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

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

"""Evaluación de un modelo entrenado sobre los splits temporales."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from ..config import Settings
from ..data.temporal_split import SplitName, TemporalSplit
from ..features import read_artifacts
from .metrics import binary_metrics
from .train_online import load_model, split_mask


def evaluate_model(
    settings: Settings,
    *,
    split: SplitName = SplitName.TEST,
    model_path: Path | None = None,
) -> dict:
    """Evalúa el modelo congelado en ``split`` y escribe ``model_<split>.json``."""
    artifact = load_model(settings, model_path)
    model = artifact["model"]

    artifacts = read_artifacts(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()
    mask = split_mask(steps, split, TemporalSplit())

    x = np.asarray(features[mask], dtype=np.float32)
    y = np.asarray(labels[mask], dtype=np.int8)
    scores = model.predict_proba(x)[:, 1]
    metrics = binary_metrics(y, scores, float(artifact["threshold"]))

    payload = {
        "dataset": "paysim",
        "split": split.value,
        "threshold": float(artifact["threshold"]),
        "feature_version": artifact["feature_version"],
        "model_version": artifact["model_version"],
        "metrics": metrics,
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / f"model_{split.value}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload

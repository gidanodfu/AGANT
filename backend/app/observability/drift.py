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

"""Drift de features y de etiqueta sobre splits temporales (offline).

No mezcla observaciones de replay con métricas live: es un análisis
offline del dataset. La variación temporal de PaySim se documenta como
fenómeno del dataset.
"""

from __future__ import annotations

import numpy as np

from ..config import Settings
from ..contracts.transaction import MODEL_FEATURE_NAMES
from ..data.temporal_split import TemporalSplit
from ..features import load_meta, read_artifacts

_CACHE: dict[str, dict] = {}


def _sample_indices(mask: np.ndarray, sample: int) -> np.ndarray:
    indices = np.flatnonzero(mask)
    if indices.size <= sample:
        return indices
    step = indices.size // sample
    return indices[::step][:sample]


def _stats(features: np.ndarray, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    block = np.asarray(features[indices], dtype=np.float64)
    return block.mean(axis=0), block.std(axis=0)


def reference_stats(settings: Settings, *, sample: int = 50_000) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Medias/desviaciones de referencia (TRAIN) para comparar con LIVE."""
    artifacts = read_artifacts(settings)
    features = artifacts.load_features()
    steps = artifacts.load_steps()
    indices = _sample_indices(steps <= TemporalSplit().train_end, sample)
    mean, std = _stats(features, indices)
    return list(MODEL_FEATURE_NAMES), mean, std


def drift_report(settings: Settings, *, sample: int = 50_000, force: bool = False) -> dict:
    key = str(settings.processed_data_path / "paysim" / "features.f32")
    if not force and key in _CACHE:
        payload = _CACHE[key]
    else:
        payload = _compute(settings, sample)
        _CACHE[key] = payload
    return payload


def _compute(settings: Settings, sample: int) -> dict:
    artifacts = read_artifacts(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()
    temporal = TemporalSplit()

    train_idx = _sample_indices(steps <= temporal.train_end, sample)
    test_idx = _sample_indices(steps >= temporal.validation_end + 1, sample)
    train_mean, train_std = _stats(features, train_idx)
    test_mean, _ = _stats(features, test_idx)
    eps = 1e-9
    feature_drift = {
        name: {
            "train_mean": float(train_mean[i]),
            "test_mean": float(test_mean[i]),
            "standardized_diff": float((test_mean[i] - train_mean[i]) / (train_std[i] + eps)),
        }
        for i, name in enumerate(MODEL_FEATURE_NAMES)
    }

    train_rate = float(labels[steps <= temporal.train_end].mean())
    test_rate = float(labels[steps >= temporal.validation_end + 1].mean())
    return {
        "dataset": "paysim",
        "feature_version": load_meta(settings).get("feature_version"),
        "sample": int(sample),
        "feature_drift": feature_drift,
        "label_drift": {
            "train_rate": train_rate,
            "test_rate": test_rate,
            "ratio": (test_rate / train_rate) if train_rate else None,
        },
        "note": "Análisis offline; no representa tráfico live de producción.",
    }

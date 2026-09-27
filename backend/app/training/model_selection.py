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

"""Selección de modelo (RF vs GBM) con umbral en VALIDATION y latencia.

Comparación justa: mismo split temporal, mismas 15 features, umbral elegido
por F1 en VALIDATION (nunca en TEST) y medición de latencia per-item. No
modifica el modelo servido; sólo produce evidencia para decidir.
"""

from __future__ import annotations

import time

import numpy as np

from ..config import Settings
from ..data.temporal_split import SplitName
from ..features import load_meta, read_artifacts
from .metrics import binary_metrics
from .thresholds import DEFAULT_THRESHOLDS, select_threshold
from .train_online import GBM_PARAMS, RF_PARAMS, build_model, split_mask


def _percentiles(values: list[float]) -> dict:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}
    ordered = sorted(values)
    n = len(ordered)

    def at(q: float) -> float:
        return ordered[min(n - 1, int(q * (n - 1)))]

    return {"p50": at(0.50), "p95": at(0.95), "p99": at(0.99), "count": n}


def _per_item_latency(model, matrix: np.ndarray, sample: int = 2000) -> dict:
    """Latencia de ``predict_proba`` fila a fila (ruta de ``/decision``)."""
    rows = matrix[: min(sample, matrix.shape[0])]
    timings = []
    for row in rows:
        start = time.perf_counter()
        model.predict_proba(np.asarray([row], dtype=np.float32))
        timings.append((time.perf_counter() - start) * 1000.0)
    return _percentiles(timings)


def evaluate_candidate(kind: str, features, labels, steps) -> dict:
    train = split_mask(steps, SplitName.TRAIN)
    x_train = np.asarray(features[train], dtype=np.float32)
    y_train = np.asarray(labels[train], dtype=np.int8)

    model = build_model(kind)
    start = time.time()
    model.fit(x_train, y_train)
    train_seconds = time.time() - start
    # Igual que el servicio: n_jobs=1 en inferencia (el paralelismo por fila
    # añade overhead y falsea la comparación de latencia).
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1

    val_mask = split_mask(steps, SplitName.VALIDATION)
    x_val = np.asarray(features[val_mask], dtype=np.float32)
    y_val = np.asarray(labels[val_mask])
    val_scores = model.predict_proba(x_val)[:, 1]
    selected = select_threshold(y_val, val_scores, "f1", DEFAULT_THRESHOLDS)
    threshold = float(selected["best"]["threshold"])

    test_mask = split_mask(steps, SplitName.TEST)
    x_test = np.asarray(features[test_mask], dtype=np.float32)
    y_test = np.asarray(labels[test_mask])
    test_scores = model.predict_proba(x_test)[:, 1]

    return {
        "kind": kind,
        "params": RF_PARAMS if kind == "rf" else GBM_PARAMS,
        "train_seconds": train_seconds,
        "threshold": threshold,
        "validation": binary_metrics(y_val, val_scores, threshold),
        "test": binary_metrics(y_test, test_scores, threshold),
        "latency_ms": _per_item_latency(model, x_test),
    }


def compare_models(settings: Settings) -> dict:
    artifacts = read_artifacts(settings)
    meta = load_meta(settings)
    features = artifacts.load_features(mode="r")
    labels = artifacts.load_labels(mode="r")
    steps = artifacts.load_steps(mode="r")
    return {
        "dataset": "paysim",
        "feature_version": meta["feature_version"],
        "candidates": {
            kind: evaluate_candidate(kind, features, labels, steps)
            for kind in ("rf", "gbm")
        },
    }


def choose_winner(
    comparison: dict, *, metric: str = "f1", latency_ratio: float = 1.5
) -> dict:
    """Recomienda GBM sólo si mejora en TEST sin exceder el margen de latencia.

    La latencia de referencia es el p95 per-item del RF. Si el GBM supera ese
    p95 por más de ``latency_ratio``, se conserva el RF (sin regresión online).
    """
    rf = comparison["candidates"]["rf"]
    gbm = comparison["candidates"]["gbm"]
    rf_metric = float(rf["test"][metric])
    gbm_metric = float(gbm["test"][metric])
    rf_p95 = float(rf["latency_ms"]["p95"])
    gbm_p95 = float(gbm["latency_ms"]["p95"])
    quality_win = gbm_metric > rf_metric
    latency_ok = gbm_p95 <= latency_ratio * rf_p95 if rf_p95 > 0 else True
    return {
        "winner": "gbm" if (quality_win and latency_ok) else "rf",
        "metric": metric,
        "rf_test": rf_metric,
        "gbm_test": gbm_metric,
        "rf_p95_ms": rf_p95,
        "gbm_p95_ms": gbm_p95,
        "quality_win": quality_win,
        "latency_ok": latency_ok,
        "latency_ratio": latency_ratio,
    }

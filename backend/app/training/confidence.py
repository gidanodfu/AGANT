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

"""Intervalos de confianza por bootstrap para métricas de clasificación.

Remuestrea con reemplazo el conjunto evaluado y resume media, desviación y
percentiles 2.5/97.5 de cada métrica. Puro y determinista con ``seed`` fijo.
"""

from __future__ import annotations

import numpy as np

from .metrics import binary_metrics

DEFAULT_METRICS = ("precision", "recall", "f1", "roc_auc", "pr_auc")


def _summarize(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "std": None, "low": None, "high": None, "count": 0}
    array = np.asarray(values, dtype=np.float64)
    low, high = np.percentile(array, [2.5, 97.5])
    return {
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if array.size > 1 else 0.0,
        "low": float(low),
        "high": float(high),
        "count": int(array.size),
    }


def bootstrap_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
    *,
    n: int = 1000,
    seed: int = 42,
    metrics: tuple[str, ...] = DEFAULT_METRICS,
) -> dict:
    """Resume las métricas por bootstrap (percentil 2.5–97.5)."""
    y_true = np.asarray(y_true).astype(np.int8)
    y_score = np.asarray(y_score, dtype=np.float64)
    size = y_true.shape[0]
    samples: dict[str, list[float]] = {key: [] for key in metrics}
    rng = np.random.default_rng(seed)
    for _ in range(n):
        index = rng.integers(0, size, size)
        resampled_y = y_true[index]
        if resampled_y.min() == resampled_y.max():
            continue  # remuestreo sin ambas clases: métrica indefinida
        result = binary_metrics(resampled_y, y_score[index], threshold)
        for key in metrics:
            value = result.get(key)
            if value is not None:
                samples[key].append(float(value))
    return {
        "threshold": float(threshold),
        "n": n,
        "seed": seed,
        "point": {key: binary_metrics(y_true, y_score, threshold)[key] for key in metrics},
        "ci": {key: _summarize(values) for key, values in samples.items()},
    }

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

"""Selección de umbral sobre VALIDATION (congelado antes de TEST)."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score

from .metrics import binary_metrics

# Rejilla fina hacia umbrales altos (pesos balanceados concentran scores ~1).
DEFAULT_THRESHOLDS: list[float] = [round(float(x), 4) for x in np.linspace(0.05, 0.999, 96)]


def sweep_thresholds(
    y_true: np.ndarray, y_score: np.ndarray, thresholds: list[float] | None = None
) -> list[dict]:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    y_true = np.asarray(y_true).astype(np.int8)
    y_score = np.asarray(y_score, dtype=np.float64)
    rows = []
    for threshold in thresholds:
        y_pred = (y_score >= threshold).astype(np.int8)
        rows.append(
            {
                "threshold": float(threshold),
                "precision": float(precision_score(y_true, y_pred, zero_division=0.0)),
                "recall": float(recall_score(y_true, y_pred, zero_division=0.0)),
                "f1": float(f1_score(y_true, y_pred, zero_division=0.0)),
            }
        )
    return rows


def select_threshold(
    y_true: np.ndarray,
    y_score: np.ndarray,
    metric: str = "f1",
    thresholds: list[float] | None = None,
) -> dict:
    """Devuelve el umbral que maximiza ``metric`` en la rejilla evaluada."""
    rows = sweep_thresholds(y_true, y_score, thresholds)
    best = max(rows, key=lambda row: row[metric])
    return {"best": best, "sweep": rows, "metric": metric}

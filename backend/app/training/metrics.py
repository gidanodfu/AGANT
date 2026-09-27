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

"""Métricas de clasificación binaria para evaluación de modelos."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def binary_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict:
    y_true = np.asarray(y_true).astype(np.int8)
    y_score = np.asarray(y_score, dtype=np.float64)
    y_pred = (y_score >= threshold).astype(np.int8)

    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())

    zero_division = 0.0
    metrics = {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, y_pred, zero_division=zero_division)),
        "recall": float(recall_score(y_true, y_pred, zero_division=zero_division)),
        "f1": float(f1_score(y_true, y_pred, zero_division=zero_division)),
        "roc_auc": float(roc_auc_score(y_true, y_score)) if y_true.min() != y_true.max() else None,
        "pr_auc": (
            float(average_precision_score(y_true, y_score))
            if y_true.min() != y_true.max()
            else None
        ),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "rows": int(y_true.shape[0]),
        "fraud": int(y_true.sum()),
    }
    return metrics

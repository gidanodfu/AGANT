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

"""Variante ``audit_only`` con features post-transacción.

Usa ``newbalanceOrig/newbalanceDest`` (información que sólo existe **después**
de ejecutar la operación). Sirve para auditoría/techo teórico; **nunca** se usa
en la ruta online ni como modelo de producción.
"""

from __future__ import annotations

import json
import time

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from ..config import Settings
from ..data.paysim_db import connect
from .metrics import binary_metrics

AUDIT_FEATURE_NAMES = (
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "type_CASH_IN",
    "type_CASH_OUT",
    "type_DEBIT",
    "type_PAYMENT",
    "type_TRANSFER",
)

_PARAMS = {
    "n_estimators": 15,
    "max_depth": 20,
    "min_samples_leaf": 2,
    "max_features": "sqrt",
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1,
}


def _query(settings: Settings, where: str, limit: str = "") -> tuple[np.ndarray, np.ndarray]:
    sql = f"""
        SELECT amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest,
               (type='CASH_IN')::INT AS type_CASH_IN,
               (type='CASH_OUT')::INT AS type_CASH_OUT,
               (type='DEBIT')::INT AS type_DEBIT,
               (type='PAYMENT')::INT AS type_PAYMENT,
               (type='TRANSFER')::INT AS type_TRANSFER,
               isFraud
        FROM transactions WHERE {where} ORDER BY row_id {limit}
    """
    data = connect(settings).execute(sql).fetchnumpy()
    import pandas as pd

    frame = pd.DataFrame(data)
    x = frame[list(AUDIT_FEATURE_NAMES)].to_numpy(dtype=np.float32)
    y = frame["isFraud"].to_numpy(dtype=np.int8)
    return x, y


def train_audit_only(settings: Settings, *, train_limit: int = 1_500_000) -> dict:
    x_train, y_train = _query(settings, "step <= 520", f"LIMIT {train_limit}")
    x_test, y_test = _query(settings, "step >= 632")
    model = RandomForestClassifier(**_PARAMS)
    model.fit(x_train, y_train)
    metrics = binary_metrics(y_test, model.predict_proba(x_test)[:, 1], 0.5)
    payload = {
        "model": "RandomForestClassifier",
        "variant": "audit_only",
        "audit_only": True,
        "warning": "Usa features post-transacción; NO es apto para inferencia online.",
        "feature_names": list(AUDIT_FEATURE_NAMES),
        "split": "test",
        "threshold": 0.5,
        "train_rows": int(x_train.shape[0]),
        "metrics": metrics,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    settings.models_path.mkdir(parents=True, exist_ok=True)
    (settings.models_path / "random_forest_audit_only.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload

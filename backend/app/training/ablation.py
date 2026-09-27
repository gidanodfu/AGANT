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

"""Ablación online: 9 features tabulares vs + 6 de grafo."""

from __future__ import annotations

import time

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from ..config import Settings
from ..data.temporal_split import SplitName
from ..features import read_artifacts
from .metrics import binary_metrics
from .train_online import RF_PARAMS as _ONLINE_PARAMS
from .train_online import split_mask

_PARAMS = {**_ONLINE_PARAMS, "n_estimators": 15}


def _train_variant(settings: Settings, graph: bool, *, limit: int = 2_000_000) -> dict:
    artifacts = read_artifacts(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()

    train_mask = split_mask(steps, SplitName.TRAIN)
    val_mask = split_mask(steps, SplitName.VALIDATION)

    x_train = np.asarray(features[train_mask], dtype=np.float32)
    y_train = np.asarray(labels[train_mask], dtype=np.int8)
    x_val = np.asarray(features[val_mask], dtype=np.float32)
    y_val = np.asarray(labels[val_mask], dtype=np.int8)
    if x_train.shape[0] > limit:
        step = x_train.shape[0] // limit
        x_train = x_train[::step][:limit]
        y_train = y_train[::step][:limit]
    if not graph:
        x_train = x_train[:, :9]
        x_val = x_val[:, :9]

    model = RandomForestClassifier(**_PARAMS)
    model.fit(x_train, y_train)
    metrics = binary_metrics(y_val, model.predict_proba(x_val)[:, 1], 0.5)
    return {"graph": graph, "n_features": int(x_train.shape[1]), "metrics": metrics}


def run_ablation(settings: Settings) -> dict:
    started = time.perf_counter()
    without_graph = _train_variant(settings, graph=False)
    with_graph = _train_variant(settings, graph=True)
    return {
        "dataset": "paysim",
        "split": "validation",
        "elapsed_s": time.perf_counter() - started,
        "online_without_graph": without_graph,
        "online_with_graph": with_graph,
        "delta_f1": with_graph["metrics"]["f1"] - without_graph["metrics"]["f1"],
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

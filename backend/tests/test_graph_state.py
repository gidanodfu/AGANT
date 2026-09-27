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

"""Tests de causalidad y paridad del estado de grafo."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.config import Settings
from app.data.paysim import EXPECTED_COLUMNS
from app.data import build_database
from app.features import build_features, read_artifacts
from app.features.graph_state import GraphState

HEADER = ",".join(EXPECTED_COLUMNS)
ROWS = [
    "1,TRANSFER,10,C1,10,0,M1,0,0,0,0",
    "1,TRANSFER,10,C1,10,0,M2,0,0,0,0",
    "2,TRANSFER,10,C1,10,0,M1,0,0,0,0",
    "2,TRANSFER,10,C2,10,0,M1,0,0,0,0",
    "2,TRANSFER,10,C1,10,0,M1,0,0,0,0",
]


def test_same_step_is_invisible():
    state = GraphState(max_accounts=100, max_edges=100)
    # paso 1
    assert state.context("C1", "M1", 1).origin_degree_before == 0
    state.observe("C1", "M1", 1)
    assert state.context("C1", "M2", 1).origin_degree_before == 0
    state.observe("C1", "M2", 1)
    # paso 2: sólo ve el paso 1
    ctx = state.context("C1", "M1", 2)
    assert ctx.origin_degree_before == 2
    assert ctx.destination_degree_before == 1
    assert ctx.origin_unique_destinations_before == 2
    assert ctx.destination_unique_origins_before == 1
    assert ctx.edge_count_before == 1
    assert ctx.edge_seen_before == 1
    state.observe("C1", "M1", 2)
    assert state.context("C2", "M1", 2).destination_degree_before == 1


def test_offline_online_parity(tmp_path: Path):
    settings = Settings(data_dir=str(tmp_path / "data"), results_dir=str(tmp_path / "res"))
    csv = settings.raw_data_path / "paysim.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(HEADER + "\n" + "\n".join(ROWS) + "\n", encoding="utf-8")

    build_database(settings, force=True)
    artifacts = build_features(settings, force=True)
    features = artifacts.load_features()

    state = GraphState(max_accounts=1000, max_edges=1000)
    graph_columns = range(9, 15)
    for i, row in enumerate(ROWS):
        step, _, _, origin, _, _, dest, _, _, _, _ = row.split(",")
        context = state.context(origin, dest, int(step))
        online = [
            context.origin_degree_before,
            context.destination_degree_before,
            context.origin_unique_destinations_before,
            context.destination_unique_origins_before,
            context.edge_count_before,
            context.edge_seen_before,
        ]
        offline = [float(features[i][c]) for c in graph_columns]
        assert online == offline, f"fila {i}: online={online} offline={offline}"
        step = int(row.split(",")[0])
        state.observe(origin, dest, step)

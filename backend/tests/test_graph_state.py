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

"""Tests de causalidad y paridad del estado de grafo."""

from __future__ import annotations

import random
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


def _synth_rows(n: int, seed: int = 0, per_step: int = 100) -> list[str]:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        step = 1 + i // per_step
        origin = f"C{rng.randint(1, 500)}"
        dest = f"M{rng.randint(1, 200)}"
        amount = round(rng.uniform(1.0, 1000.0), 2)
        rows.append(f"{step},TRANSFER,{amount},{origin},{amount},0,{dest},0,0,0,0")
    return rows


def test_offline_online_parity_large(tmp_path: Path):
    settings = Settings(data_dir=str(tmp_path / "data"), results_dir=str(tmp_path / "res"))
    rows = _synth_rows(20_000)
    csv = settings.raw_data_path / "paysim.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")

    build_database(settings, force=True)
    features = build_features(settings, force=True).load_features()

    state = GraphState(max_accounts=1_000_000, max_edges=1_000_000)
    graph_columns = range(9, 15)
    for i, row in enumerate(rows):
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
        state.observe(origin, dest, int(step))


def test_offline_graph_respects_caps_under_eviction(tmp_path: Path):
    # Caps diminutos fuerzan evicción LRU; offline y online deben seguir
    # coincidiendo porque comparten el mismo GraphState.
    settings = Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        graph_max_accounts=3,
        graph_max_edges=3,
    )
    rows = _synth_rows(500)
    csv = settings.raw_data_path / "paysim.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")

    build_database(settings, force=True)
    features = build_features(settings, force=True).load_features()

    state = GraphState(max_accounts=3, max_edges=3)
    graph_columns = range(9, 15)
    for i, row in enumerate(rows):
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
        state.observe(origin, dest, int(step))

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

"""Tests del grafo por transacción (live y dataset)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.data import build_database
from app.data.paysim import EXPECTED_COLUMNS
from app.main import create_app

HEADER = ",".join(EXPECTED_COLUMNS)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        laya_enabled=False,
        laya_mode="disabled",
    )


def _write_dataset(settings: Settings, rows: int = 12) -> None:
    csv = settings.raw_data_path / "paysim.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    lines = [HEADER]
    for i in range(rows):
        lines.append(f"{i + 1},TRANSFER,{10 + i},C{i % 3},100,0,M{i % 2},0,0,0,0")
    csv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    build_database(settings, force=True)


def test_live_transaction_graph(tmp_path):
    app = create_app(_settings(tmp_path))
    payload = {
        "transaction_id": "G1",
        "step": 700,
        "type": "TRANSFER",
        "amount": 100.0,
        "name_orig": "C1",
        "old_balance_org": 100.0,
        "name_dest": "M1",
        "old_balance_dest": 0.0,
    }
    with TestClient(app) as client:
        client.post("/api/v1/decision", json=payload)
        data = client.get("/api/v1/transactions/G1/graph").json()["data"]
    node_ids = {node["id"] for node in data["graph"]["nodes"]}
    assert {"C1", "M1"} <= node_ids
    assert data["transaction"]["transaction_id"] == "G1"
    assert data["context"]["origin_degree_before"]["description"]
    assert "categories" in data and "descriptions" in data


def test_dataset_transaction_graph(tmp_path):
    settings = _settings(tmp_path)
    _write_dataset(settings)
    with TestClient(create_app(settings)) as client:
        data = client.get("/api/v1/transactions/R1/graph").json()["data"]
    assert data["transaction"]["source"] == "replay"
    assert data["transaction"]["name_orig"] == "C0"
    assert data["graph"]["nodes"]
    assert "dataset_fraud" in data


def test_unknown_transaction_returns_404(tmp_path):
    with TestClient(create_app(_settings(tmp_path)), raise_server_exceptions=False) as client:
        response = client.get("/api/v1/transactions/NOEXISTE/graph")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

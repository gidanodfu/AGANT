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

"""Tests de importación de transacciones (procesamiento real source=live)."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        laya_enabled=False,
        laya_mode="disabled",
    )


def _tx(i: int) -> dict:
    return {
        "transaction_id": f"IMP{i}",
        "step": 700,
        "type": "TRANSFER",
        "amount": 100.0 + i,
        "name_orig": f"C{i}",
        "old_balance_org": 1000.0,
        "name_dest": f"M{i}",
        "old_balance_dest": 0.0,
    }


def _wait(client: TestClient, timeout: float = 8.0) -> dict:
    deadline = time.time() + timeout
    status = {}
    while time.time() < deadline:
        status = client.get("/api/v1/flow/status").json()["data"]
        if status.get("state") in ("finished", "stopped", "error"):
            return status
        time.sleep(0.05)
    return status


def test_import_processes_transactions(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/transactions/import",
            json={"transactions": [_tx(1), _tx(2), _tx(3)], "batch_size": 32},
        ).json()["data"]
        assert started["kind"] == "import"
        assert started["total"] == 3
        status = _wait(client)
    assert status["processed"] == 3
    transactions = app.state.services.store.recent_transactions(10)
    assert {t["transaction_id"] for t in transactions} == {"IMP1", "IMP2", "IMP3"}
    assert all(t["source"] == "live" for t in transactions)


def test_import_rejects_is_fraud(tmp_path):
    bad = _tx(1)
    bad["isFraud"] = True
    with TestClient(create_app(_settings(tmp_path)), raise_server_exceptions=False) as client:
        response = client.post("/api/v1/transactions/import", json={"transactions": [bad]})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_import_rejects_empty(tmp_path):
    with TestClient(create_app(_settings(tmp_path)), raise_server_exceptions=False) as client:
        response = client.post("/api/v1/transactions/import", json={"transactions": []})
    assert response.status_code == 400

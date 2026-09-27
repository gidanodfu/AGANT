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

"""Tests de los endpoints de decisión y observabilidad."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _payload(tx_id: str = "T1", amount: float = 10.0, flagged: bool = False) -> dict:
    return {
        "transaction_id": tx_id,
        "step": 10,
        "type": "TRANSFER",
        "amount": amount,
        "name_orig": "C1",
        "old_balance_org": 100.0,
        "name_dest": "M1",
        "old_balance_dest": 0.0,
        "is_flagged_fraud": flagged,
    }


def _client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_single_decision(settings: Settings):
    with _client(settings) as client:
        response = client.post("/api/v1/decision", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["final_decision"] in ("LEGITIMATE", "SUSPICIOUS", "FRAUD")
    assert body["data"]["laya"]["status"] == "disabled"
    assert body["request_id"]


def test_flagged_transaction_forces_fraud(settings: Settings):
    with _client(settings) as client:
        response = client.post("/api/v1/decision", json=_payload(flagged=True))
    assert response.json()["data"]["final_decision"] == "FRAUD"


def test_invalid_transaction_returns_validation_error(settings: Settings):
    bad = _payload()
    bad["amount"] = -5.0
    with _client(settings) as client:
        response = client.post("/api/v1/decision", json=bad)
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_batch_decision_and_limits(settings: Settings):
    with _client(settings) as client:
        ok = client.post("/api/v1/decision/batch", json=[_payload("T1"), _payload("T2")])
        empty = client.post("/api/v1/decision/batch", json=[])
    assert ok.status_code == 200 and len(ok.json()["data"]) == 2
    assert empty.status_code == 400


def test_batch_matches_individual_decisions(settings: Settings):
    payloads = [_payload(f"T{i}", amount=10.0 + i * 5) for i in range(5)]
    with _client(settings) as client:
        individual = [
            client.post("/api/v1/decision", json=payload).json()["data"]["final_decision"]
            for payload in payloads
        ]
    with _client(settings) as client:
        batch = client.post("/api/v1/decision/batch", json=payloads).json()["data"]
    assert [item["final_decision"] for item in batch] == individual


def test_graph_endpoint_derives_nodes_and_edges(settings: Settings):
    with _client(settings) as client:
        client.post("/api/v1/decision", json=_payload())
        data = client.get("/api/v1/graph").json()["data"]
    nodes = {node["id"] for node in data["nodes"]}
    assert {"C1", "M1"} <= nodes
    assert data["edges"][0]["source"] == "C1"
    assert "RISK" in data["categories"]


def test_transactions_and_laya_decisions_endpoints(settings: Settings):
    with _client(settings) as client:
        client.post("/api/v1/decision", json=_payload())
        transactions = client.get("/api/v1/transactions").json()
        laya = client.get("/api/v1/laya-decisions").json()
        metrics = client.get("/api/v1/metrics").json()
    assert transactions["data"][0]["transaction_id"] == "T1"
    assert laya["data"] == []
    assert metrics["data"]["snapshots"]["live"]["processed"] == 1

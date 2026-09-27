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

"""Tests del flujo interactivo (/nueva-transaccion: decisión, flow live/replay)."""

from __future__ import annotations

import time
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


def _write_dataset(settings: Settings, rows: int = 20) -> None:
    csv = settings.raw_data_path / "paysim.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    lines = [HEADER]
    for i in range(rows):
        fraud = 1 if i % 10 == 0 else 0
        lines.append(f"{i + 1},TRANSFER,{10 + i},C{i},100,0,M{i},0,0,{fraud},0")
    csv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    build_database(settings, force=True)


def _payload(tx_id: str = "T1", **overrides) -> dict:
    base = {
        "transaction_id": tx_id,
        "step": 10,
        "type": "TRANSFER",
        "amount": 10.0,
        "name_orig": "C1",
        "old_balance_org": 100.0,
        "name_dest": "M1",
        "old_balance_dest": 0.0,
    }
    base.update(overrides)
    return base


def _wait_status(client: TestClient, target=("finished", "stopped"), timeout=8.0) -> dict:
    deadline = time.time() + timeout
    status = {}
    while time.time() < deadline:
        status = client.get("/api/v1/flow/status").json()["data"]
        if status.get("state") in target:
            return status
        time.sleep(0.05)
    return status


def test_flow_status_idle(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        data = client.get("/api/v1/flow/status").json()["data"]
    assert data["state"] == "idle"


def test_decision_response_has_event_id(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        data = client.post("/api/v1/decision", json=_payload()).json()["data"]
    assert data["event_id"] == "live:decision.created:T1"
    assert "serialization_ms" in data["latency"]


def test_is_fraud_is_rejected(tmp_path):
    with TestClient(create_app(_settings(tmp_path)), raise_server_exceptions=False) as client:
        response = client.post("/api/v1/decision", json=_payload(isFraud=True))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_flow_replay_publishes_replay_source(tmp_path):
    settings = _settings(tmp_path)
    _write_dataset(settings, rows=20)
    app = create_app(settings)
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/flow/start",
            json={"source": "replay", "count": 20, "laya_mode": "disabled"},
        ).json()["data"]
        assert started["source"] == "replay"
        status = _wait_status(client)
    assert status["state"] in ("finished", "stopped")
    assert status["processed"] == 20
    assert status["source"] == "replay"

    transactions = app.state.services.store.recent_transactions(50, None)
    assert transactions and all(tx["source"] == "replay" for tx in transactions)


def test_flow_replay_all_processes_whole_dataset(tmp_path):
    settings = _settings(tmp_path)
    _write_dataset(settings, rows=20)
    app = create_app(settings)
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/flow/start",
            json={"source": "replay", "count": "all", "batch_size": 32, "laya_mode": "disabled"},
        ).json()["data"]
        assert started["total"] == 20  # precalculado (ETA desde el inicio)
        status = _wait_status(client)
    assert status["state"] in ("finished", "stopped")
    assert status["processed"] == 20


def test_flow_start_accepts_decision_mode(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/flow/start",
            json={
                "source": "live",
                "count": 50,
                "batch_size": 32,
                "laya_mode": "disabled",
                "decision_mode": "laya_all",
            },
        ).json()["data"]
        assert started["decision_mode"] == "laya_all"
        status = _wait_status(client)
    assert status["processed"] == 50
    assert status["decision_mode"] == "laya_all"


def test_system_status_exposes_decision_mode(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        data = client.get("/api/v1/system/status").json()["data"]
    assert data["decision_mode"] in ("hybrid", "laya_all")


def test_flow_live_all_is_rejected(tmp_path):
    with TestClient(create_app(_settings(tmp_path)), raise_server_exceptions=False) as client:
        response = client.post("/api/v1/flow/start", json={"source": "live", "count": "all"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REPLAY_ERROR"


def test_flow_live_generates_synthetic_source(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        client.post(
            "/api/v1/flow/start",
            json={"source": "live", "count": 50, "laya_mode": "disabled"},
        )
        status = _wait_status(client)
    assert status["state"] in ("finished", "stopped")
    assert status["source"] == "live_synthetic"
    assert status["processed"] == 50

    transactions = app.state.services.store.recent_transactions(50, None)
    assert transactions and all(tx["source"] == "live_synthetic" for tx in transactions)


def test_flow_stop_preserves_stats(tmp_path):
    settings = _settings(tmp_path)
    _write_dataset(settings, rows=2000)
    app = create_app(settings)
    with TestClient(app) as client:
        client.post(
            "/api/v1/flow/start",
            json={"source": "replay", "count": 2000, "laya_mode": "disabled"},
        )
        deadline = time.time() + 6
        while time.time() < deadline:
            current = client.get("/api/v1/flow/status").json()["data"]
            if current.get("processed", 0) > 0:
                break
            time.sleep(0.05)
        stopped = client.post("/api/v1/flow/stop", json={}).json()["data"]
    assert stopped["state"] in ("stopped", "finished")
    assert stopped["processed"] >= 0
    assert "fraud" in stopped and "latency_p95_ms" in stopped


def test_flow_custom_without_any_subfolder_errors(tmp_path):
    settings = _settings(tmp_path)
    settings = settings.model_copy(update={"laya_subfolders": "", "laya_custom_subfolder": None})
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/flow/start",
            json={"source": "live", "count": 10, "laya_mode": "custom"},
        )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "subcarpeta" in body["error"]["message"]


def test_system_status_exposes_laya_subfolders(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        data = client.get("/api/v1/system/status").json()["data"]
    assert data["laya_custom_available"] is True
    assert "typed-decisions" in data["laya_subfolders"]


def test_decision_event_includes_context(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        queue = app.state.services.bus.subscribe()
        client.post("/api/v1/decision", json=_payload("CTX1"))
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())
    decisions = [e for e in events if e.event_type.value == "decision.created"]
    assert decisions
    payload = decisions[0].payload
    assert payload["transaction"]["type"] == "TRANSFER"
    assert payload["transaction"]["amount"] == 10.0
    evidence = payload["state"]["evidence"]
    assert "rules" in evidence
    assert "context" in evidence["graph"]
    assert "features" in payload["state"]


def test_validation_error_publishes_system_error(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=False) as client:
        queue = app.state.services.bus.subscribe()
        client.post("/api/v1/decision", json=_payload(isFraud=True))
        codes = []
        while not queue.empty():
            event = queue.get_nowait()
            if event.event_type.value == "system.error":
                codes.append(event.payload["code"])
    assert "VALIDATION_ERROR" in codes


def test_flow_status_event_ids_are_unique(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        queue = app.state.services.bus.subscribe()
        client.post(
            "/api/v1/flow/start",
            json={"source": "live", "count": 1500, "laya_mode": "disabled"},
        )
        status = _wait_status(client)
        ids = []
        while not queue.empty():
            event = queue.get_nowait()
            if event.event_type.value == "flow.status":
                ids.append(event.event_id)
    assert status["state"] in ("finished", "stopped")
    assert len(ids) >= 2
    assert len(set(ids)) == len(ids)


def test_decisions_endpoint(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        client.post("/api/v1/decision", json=_payload())
        data = client.get("/api/v1/decisions").json()["data"]
    assert data and data[0]["transaction_id"] == "T1"


def test_flow_count_validation(tmp_path):
    with TestClient(create_app(_settings(tmp_path)), raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/flow/start", json={"source": "live", "count": 0}
        )
    assert response.status_code == 400

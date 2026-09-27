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

"""Tests de WebSocket (eventos) y validación de origen."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.main import create_app


def _payload(tx_id: str = "T1") -> dict:
    return {
        "transaction_id": tx_id,
        "step": 10,
        "type": "TRANSFER",
        "amount": 10.0,
        "name_orig": "C1",
        "old_balance_org": 100.0,
        "name_dest": "M1",
        "old_balance_dest": 0.0,
    }


def _settings(tmp_path, origin: str) -> Settings:
    return Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        laya_enabled=False,
        laya_mode="disabled",
        allowed_ws_origins=origin,
    )


def test_ws_receives_decision_event(tmp_path):
    app = create_app(_settings(tmp_path, ""))
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/events") as ws:
            client.post("/api/v1/decision", json=_payload())
            first = ws.receive_json()
            second = ws.receive_json()
    types = {first["event_type"], second["event_type"]}
    assert "transaction.created" in types
    assert "decision.created" in types
    assert first["source"] == "live"
    assert first["event_id"]


def test_ws_rejects_disallowed_origin(tmp_path):
    app = create_app(_settings(tmp_path, "http://permitido.test"))
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/api/v1/ws/events", headers={"origin": "http://malicioso.test"}
            ) as ws:
                ws.receive_json()

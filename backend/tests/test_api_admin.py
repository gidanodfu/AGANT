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

"""Tests de protección de endpoints administrativos."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings(tmp_path, token: str | None) -> Settings:
    return Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        laya_enabled=False,
        laya_mode="disabled",
        admin_token=token,
    )


def test_admin_disabled_when_no_token(tmp_path):
    with TestClient(create_app(_settings(tmp_path, None)), raise_server_exceptions=False) as client:
        response = client.post("/api/v1/replay/start", json={"with_laya": False})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_requires_correct_token(tmp_path):
    app = create_app(_settings(tmp_path, "secreto"))
    with TestClient(app, raise_server_exceptions=False) as client:
        missing = client.post("/api/v1/replay/start", json={"with_laya": False})
        wrong = client.post(
            "/api/v1/replay/start", json={"with_laya": False}, headers={"X-Admin-Token": "nope"}
        )
        correct = client.post(
            "/api/v1/replay/start", json={"with_laya": False}, headers={"X-Admin-Token": "secreto"}
        )
    assert missing.status_code == 401
    assert wrong.status_code == 401
    # Autenticación superada; sin dataset el replay responde 409.
    assert correct.status_code == 409


def test_replay_status_is_public(tmp_path):
    with TestClient(create_app(_settings(tmp_path, "secreto"))) as client:
        response = client.get("/api/v1/replay/status")
    assert response.status_code == 200
    assert response.json()["data"]["state"] == "idle"

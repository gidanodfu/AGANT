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

"""Tests de la API base y del manejo de errores HTTP."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_health_ok_and_request_id(settings: Settings):
    with _client(settings) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["status"] in ("ready", "degraded")
    assert response.headers["X-Request-ID"]


def test_system_status_lists_components(settings: Settings):
    with _client(settings) as client:
        response = client.get("/api/v1/system/status")
    body = response.json()
    assert body["success"] is True
    assert "config" in body["data"]["components"]
    assert body["data"]["components"]["laya"] == "disabled"


def test_unhandled_error_is_safe(settings: Settings):
    app: FastAPI = create_app(settings)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("/home/privado/secreto token=xyz")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "secreto" not in body["error"]["message"]
    assert "privado" not in str(body)

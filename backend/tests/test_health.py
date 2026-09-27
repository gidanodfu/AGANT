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

"""Caracteriza el estado reportado por /health."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_ready_when_model_missing(settings: Settings):
    with TestClient(create_app(settings)) as client:
        body = client.get("/health").json()
    assert body["data"]["status"] == "ready"


def test_health_lists_degraded_components(settings: Settings):
    with TestClient(create_app(settings)) as client:
        data = client.get("/health").json()["data"]
    assert "degraded_components" in data
    assert "model" in data["degraded_components"]


def test_health_strict_marks_service_degraded(tmp_path: Path):
    settings = Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "results"),
        laya_enabled=False,
        laya_mode="disabled",
        health_strict=True,
    )
    with TestClient(create_app(settings)) as client:
        body = client.get("/health").json()
    assert body["data"]["status"] == "degraded"


def test_system_status_reports_model_component(settings: Settings):
    with TestClient(create_app(settings)) as client:
        data = client.get("/api/v1/system/status").json()["data"]
    assert "model" in data["components"]

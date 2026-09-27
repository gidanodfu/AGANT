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

"""Tests del panel de Laya (status/load/test) sin cargar GPU."""

from __future__ import annotations

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


def test_laya_status(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        data = client.get("/api/v1/laya/status").json()["data"]
    assert data["status"] == "disabled"
    assert "typed-decisions" in data["subfolders"]
    assert "vram" in data


def test_laya_load_disabled(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        data = client.post("/api/v1/laya/load", json={"mode": "disabled"}).json()["data"]
    assert data["status"] == "disabled"
    assert data["laya_active"] is False


def test_laya_test_disabled(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        data = client.post("/api/v1/laya/test", json={}).json()["data"]
    assert data["status"] in ("disabled", "unavailable")
    assert data["invoked"] is False

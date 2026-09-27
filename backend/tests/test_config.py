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

"""Tests de configuración y validación de variables."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import REPO_ROOT, Settings


def test_defaults_are_sane():
    settings = Settings()
    assert settings.threshold_suspicious == 0.2
    assert settings.threshold_fraud == 0.5
    assert settings.laya_mode == "pretrained"
    assert settings.chunk_rows == 250_000
    assert settings.data_path == (REPO_ROOT / "data").resolve()


def test_band_thresholds_must_be_ordered():
    with pytest.raises(ValidationError):
        Settings(threshold_suspicious=0.6, threshold_fraud=0.5)
    with pytest.raises(ValidationError):
        Settings(threshold_suspicious=-0.1)


def test_invalid_laya_mode_rejected():
    with pytest.raises(ValidationError):
        Settings(laya_mode="turbo")


def test_custom_laya_requires_subfolder():
    with pytest.raises(ValidationError):
        Settings(laya_mode="custom", laya_custom_subfolder=None)
    ok = Settings(laya_mode="custom", laya_custom_subfolder="mi-checkpoint")
    assert ok.laya_active_subfolder == "mi-checkpoint"


def test_env_override(monkeypatch):
    monkeypatch.setenv("AGANT_THRESHOLD_FRAUD", "0.9")
    monkeypatch.setenv("AGANT_CHUNK_ROWS", "1000")
    settings = Settings()
    assert settings.threshold_fraud == 0.9
    assert settings.chunk_rows == 1000


def test_cors_list_parsing():
    settings = Settings(cors_origins="http://a.test, http://b.test,")
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]

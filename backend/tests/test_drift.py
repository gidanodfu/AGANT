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

"""Tests del reporte de drift (requieren memmaps generados)."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.observability.drift import drift_report

settings = get_settings()
_HAS_FEATURES = (settings.processed_data_path / "paysim" / "features.f32").exists()

pytestmark = pytest.mark.skipif(not _HAS_FEATURES, reason="features PaySim no generadas")


def test_drift_report_shape():
    report = drift_report(settings, sample=5000, force=True)
    assert report["dataset"] == "paysim"
    assert len(report["feature_drift"]) == 15
    assert "amount" in report["feature_drift"]
    assert set(report["label_drift"]) >= {"train_rate", "test_rate", "ratio"}
    assert report["label_drift"]["test_rate"] >= report["label_drift"]["train_rate"]

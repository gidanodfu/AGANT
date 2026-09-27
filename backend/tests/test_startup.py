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

"""Tests de la validación de arranque."""

from __future__ import annotations

from app.config import Settings
from app.contracts import ComponentStatus
from app.observability import ComponentCheck, StartupReport, collect_startup_report


def test_report_is_ready_even_with_optional_components_missing(settings: Settings):
    report = collect_startup_report(settings)
    assert report.ready
    summary = report.summary()
    assert summary.startswith("AGANT READY")
    assert report.component_status()["config"] == "ready"


def test_required_component_failure_degrades():
    report = StartupReport(
        components=[ComponentCheck("config", ComponentStatus.FAILED, required=True)]
    )
    assert not report.ready
    assert report.summary().startswith("AGANT DEGRADED")


def test_laya_disabled_is_reported(settings: Settings):
    report = collect_startup_report(settings)
    assert report.component_status()["laya"] == "disabled"

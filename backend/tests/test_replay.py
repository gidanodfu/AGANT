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

"""Tests de replay: separación de métricas, source y propagación de Laya."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.api.state import Store
from app.config import Settings
from app.contracts.enums import Source
from app.data import build_database
from app.data.paysim import EXPECTED_COLUMNS
from app.decision import LayaDecisionEngine
from app.events import EventBus
from app.observability import MetricsCollector
from app.replay import LiveFlowEngine, ReplayController, ReplayEngine

HEADER = ",".join(EXPECTED_COLUMNS)
ROWS = [
    "1,TRANSFER,100,C1,100,0,M1,0,0,0,0",
    "2,TRANSFER,200,C1,100,0,M1,0,0,0,0",
    "3,CASH_OUT,300,C2,300,0,C3,0,0,0,0",
]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        laya_enabled=False,
        laya_mode="disabled",
    )


def _write_dataset(settings: Settings) -> None:
    csv = settings.raw_data_path / "paysim.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(HEADER + "\n" + "\n".join(ROWS) + "\n", encoding="utf-8")
    build_database(settings, force=True)


def _state(settings: Settings):
    laya = LayaDecisionEngine(settings.model_copy(update={"laya_enabled": False, "laya_mode": "disabled"}))
    return SimpleNamespace(
        settings=settings,
        bus=EventBus(),
        metrics=MetricsCollector(),
        store=Store(),
        laya=laya,
    )


def test_replay_does_not_contaminate_live(tmp_path: Path):
    settings = _settings(tmp_path)
    _write_dataset(settings)
    state = _state(settings)

    engine = ReplayEngine(state, with_laya=False, max_records=3)
    asyncio.run(engine.run())

    assert state.metrics.snapshot(Source.REPLAY).processed == 3
    assert state.metrics.snapshot(Source.LIVE).processed == 0
    transactions = state.store.recent_transactions(10)
    assert transactions and all(tx["source"] == "replay" for tx in transactions)


def test_with_laya_flag_is_propagated(tmp_path: Path):
    settings = _settings(tmp_path)
    _write_dataset(settings)
    state = _state(settings)

    without = ReplayEngine(state, with_laya=False, max_records=1)
    assert without.laya_active is False

    with_flag = ReplayEngine(state, with_laya=True, max_records=1)
    # Laya deshabilitado en el estado: no se activa aunque se pida.
    assert with_flag.laya_active is False


def test_live_flow_respects_publish_false(tmp_path: Path):
    settings = _settings(tmp_path)
    state = _state(settings)
    engine = LiveFlowEngine(state, count=20, laya_mode="disabled", publish=False)
    asyncio.run(engine.run())
    assert engine.processed == 20
    assert state.bus.events_published == 0
    assert state.metrics.snapshot(Source.LIVE).processed == 20


def test_live_flow_surfaces_error(tmp_path: Path):
    settings = _settings(tmp_path)
    state = _state(settings)
    engine = LiveFlowEngine(state, count=10, laya_mode="disabled", publish=False)

    def boom(_rows):
        raise RuntimeError("fallo simulado")

    engine._decide_block = boom
    asyncio.run(engine.run())
    assert engine.finished is True
    assert engine.error == "RuntimeError"
    payload = engine.status_payload("error")
    assert payload["error"] == "RuntimeError"


def test_controller_status_state_machine(tmp_path: Path):
    settings = _settings(tmp_path)
    _write_dataset(settings)
    state = _state(settings)
    controller = ReplayController(state)

    assert controller.status()["state"] == "idle"

    async def run():
        await controller.start(with_laya=False, max_records=3)
        await controller.stop()
        return controller.status()

    status = asyncio.run(run())
    assert status["state"] in ("finished", "stopped")
    assert status["total"] == 3

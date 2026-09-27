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

"""Tests del modo por lotes (batch): paridad con per-item y controles."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.state import Store
from app.config import Settings
from app.contracts.enums import Source
from app.decision import LayaDecisionEngine
from app.events import EventBus
from app.main import create_app
from app.observability import MetricsCollector
from app.replay import LiveFlowEngine


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=str(tmp_path / "data"),
        results_dir=str(tmp_path / "res"),
        laya_enabled=False,
        laya_mode="disabled",
    )


def _state(settings: Settings) -> SimpleNamespace:
    laya = LayaDecisionEngine(
        settings.model_copy(update={"laya_enabled": False, "laya_mode": "disabled"})
    )
    return SimpleNamespace(
        settings=settings,
        bus=EventBus(),
        metrics=MetricsCollector(),
        store=Store(),
        laya=laya,
    )


def _run(settings: Settings, batch_size: int) -> list[tuple[str, str]]:
    state = _state(settings)
    engine = LiveFlowEngine(
        state, count=300, laya_mode="disabled", publish=False, seed=7, batch_size=batch_size
    )
    asyncio.run(engine.run())
    decisions = state.store.recent_decisions(500)
    return [(d["transaction_id"], d["final_decision"]) for d in decisions]


def test_batch_matches_per_item_decisions(tmp_path: Path):
    settings = _settings(tmp_path)
    per_item = _run(settings, batch_size=1)
    batched = _run(settings, batch_size=32)
    assert per_item == batched
    assert len(per_item) == 300


def test_flow_endpoint_exposes_batch_mode(tmp_path: Path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/flow/start",
            json={
                "source": "live",
                "count": 64,
                "laya_mode": "disabled",
                "batch_size": 32,
                "publish_mode": "sampled",
            },
        ).json()["data"]
        assert started["batch_mode"] is True
        assert started["batch_size"] == 32
        import time

        deadline = time.time() + 8
        status = started
        while time.time() < deadline:
            status = client.get("/api/v1/flow/status").json()["data"]
            if status.get("state") in ("finished", "stopped"):
                break
            time.sleep(0.05)
    assert status["processed"] == 64
    assert status["source"] == "live"

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

"""Tests de concurrencia: las decisiones se serializan para preservar causalidad."""

from __future__ import annotations

import asyncio
import threading
import time

from app.api.state import Store
from app.contracts import (
    Decision,
    DecisionResult,
    FallbackLevel,
    LatencyBreakdown,
    LayaResult,
    LayaStatus,
    Source,
    Transaction,
)
from app.events import EventBus
from app.observability import MetricsCollector
from app.service import DecisionService


class _TrackingEngine:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def decide(self, transaction, *, source, correlation_id):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.002)
        with self.lock:
            self.active -= 1
        return DecisionResult(
            transaction_id=transaction.transaction_id,
            source=source,
            correlation_id=correlation_id,
            primary_decision=Decision.LEGITIMATE,
            primary_score=0.1,
            laya=LayaResult(status=LayaStatus.SKIPPED),
            final_decision=Decision.LEGITIMATE,
            fallback_level=FallbackLevel.GRAPH_ML,
            fallback_reason="r",
            latency=LatencyBreakdown(total_ms=2.0),
        )


class _State:
    def __init__(self):
        self.bus = EventBus()
        self.metrics = MetricsCollector()
        self.store = Store()
        self.decision_engine = _TrackingEngine()


def _tx(i: int) -> Transaction:
    return Transaction(
        transaction_id=f"T{i}",
        step=i,
        type="PAYMENT",
        amount=1.0,
        name_orig=f"C{i}",
        old_balance_org=1.0,
        name_dest="M1",
        old_balance_dest=0.0,
    )


def test_decisions_are_serialized():
    state = _State()
    service = DecisionService(state)

    async def run():
        await asyncio.gather(*(service.process(_tx(i)) for i in range(20)))

    asyncio.run(run())
    assert state.decision_engine.max_active == 1
    assert state.metrics.snapshot(Source.LIVE).processed == 20

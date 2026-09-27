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

"""Tests de la capa de aplicación (DecisionService)."""

from __future__ import annotations

import asyncio

from app.api.state import Store
from app.contracts import Transaction as Tx
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


class _FakeEngine:
    def decide(self, transaction, *, source, correlation_id):
        return DecisionResult(
            transaction_id=transaction.transaction_id,
            source=source,
            correlation_id=correlation_id,
            primary_decision=Decision.SUSPICIOUS,
            primary_score=0.3,
            laya=LayaResult(invoked=True, status=LayaStatus.SUCCEEDED, decision=Decision.FRAUD),
            final_decision=Decision.FRAUD,
            fallback_level=FallbackLevel.GRAPH_ML,
            fallback_reason="r",
            latency=LatencyBreakdown(total_ms=4.0),
        )


class _FakeState:
    def __init__(self):
        self.bus = EventBus()
        self.metrics = MetricsCollector()
        self.store = Store()
        self.decision_engine = _FakeEngine()


def _transaction() -> Transaction:
    return Transaction(
        transaction_id="T1",
        step=1,
        type="TRANSFER",
        amount=10.0,
        name_orig="C1",
        old_balance_org=10.0,
        name_dest="M1",
        old_balance_dest=0.0,
    )


def test_store_keeps_window_and_serializes_on_read():
    store = Store(maxlen=2)
    for i in range(3):
        store.add_transaction(
            Tx(
                transaction_id=f"T{i}",
                step=i,
                type="TRANSFER",
                amount=1.0,
                name_orig="C",
                old_balance_org=1.0,
                name_dest="D",
                old_balance_dest=0.0,
            ),
            Source.LIVE,
            f"e{i}",
        )
    items = store.recent_transactions(10)
    assert len(items) == 2
    assert items[-1]["transaction_id"] == "T2"
    assert items[-1]["source"] == "live"


def test_process_publishes_events_and_records():
    state = _FakeState()
    service = DecisionService(state)
    queue = state.bus.subscribe()

    result = asyncio.run(service.process(_transaction(), source=Source.LIVE, correlation_id="c1"))

    assert result.final_decision is Decision.FRAUD
    assert state.bus.events_published == 3  # transaction + decision + laya
    assert state.metrics.snapshot(Source.LIVE).processed == 1
    assert state.store.recent_transactions(10)[0]["transaction_id"] == "T1"
    assert state.store.recent_laya_decisions(10)[0]["laya"]["invoked"] is True

    types = []
    while not queue.empty():
        types.append(asyncio.run(queue.get()).event_type.value)
    assert "transaction.created" in types
    assert "laya.decision" in types

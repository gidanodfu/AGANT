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

"""Capa de aplicación: ejecuta la decisión y publica efectos.

No contiene lógica de reglas/ML/grafo/Laya; sólo serializa la ejecución
(causalidad del grafo), agrega métricas, guarda en el buffer reciente y
publica eventos. Mantener el orden de decisiones preserva la causalidad
aunque se ejecute fuera del bucle de eventos.
"""

from __future__ import annotations

import asyncio
import time
from functools import partial

from .contracts.decision import DecisionResult
from .contracts.enums import EventType, Source
from .contracts.events import Event, build_event_id
from .contracts.transaction import Transaction


class DecisionService:
    def __init__(self, state, engine=None) -> None:
        self.state = state
        # `record()` no necesita motor; algunos flujos por lotes construyen su
        # propio BatchDecisionEngine y reutilizan este servicio solo para
        # métricas/eventos/persistencia.
        self.engine = engine if engine is not None else getattr(state, "decision_engine", None)
        self._lock = asyncio.Lock()

    async def process(
        self,
        transaction: Transaction,
        *,
        source: Source = Source.LIVE,
        correlation_id: str = "-",
        decision_mode: str | None = None,
    ) -> DecisionResult:
        kwargs = {"source": source, "correlation_id": correlation_id}
        if decision_mode is not None:
            kwargs["decision_mode"] = decision_mode
        async with self._lock:
            result = await asyncio.to_thread(partial(self.engine.decide, transaction, **kwargs))
        self.record(result, transaction, source)
        return result

    def record(
        self,
        result: DecisionResult,
        transaction: Transaction,
        source: Source,
        *,
        publish: bool = True,
    ) -> None:
        bus = self.state.bus
        tx_event_id = build_event_id(source, EventType.TRANSACTION_CREATED, transaction.transaction_id)
        decision_event_id = build_event_id(source, EventType.DECISION_CREATED, transaction.transaction_id)
        result.event_id = decision_event_id

        if publish:
            start = time.perf_counter()
            bus.publish(
                Event.create(
                    EventType.TRANSACTION_CREATED,
                    source,
                    bus.next_sequence(),
                    transaction.transaction_id,
                    payload=transaction.model_dump(mode="json"),
                )
            )
            bus.publish(
                Event.create(
                    EventType.DECISION_CREATED,
                    source,
                    bus.next_sequence(),
                    transaction.transaction_id,
                    payload=result.model_dump(mode="json"),
                )
            )
            if result.laya.invoked:
                bus.publish(
                    Event.create(
                        EventType.LAYA_DECISION,
                        source,
                        bus.next_sequence(),
                        transaction.transaction_id,
                        payload=result.model_dump(mode="json"),
                    )
                )
            result.latency.event_ms = (time.perf_counter() - start) * 1000.0

        self.state.metrics.record_decision(result)
        if source is Source.LIVE and getattr(self.state, "live_drift", None) is not None and result.state is not None:
            self.state.live_drift.update(result.state.features)
        self.state.store.add_transaction(transaction, source, tx_event_id)
        self.state.store.add_decision(result, decision_event_id)

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

"""Importación: procesa transacciones provistas por el usuario (source=live).

No usa PaySim: son operaciones reales enviadas desde la interfaz. Devuelve
progreso por `flow.status` (kind="import") y publica eventos reales.
"""

from __future__ import annotations

import asyncio
import logging
import time

from ..config import Settings
from ..contracts.enums import Decision, EventType, Source
from ..contracts.events import Event
from ..contracts.transaction import Transaction
from ..decision import resolve_laya_engine
from ..decision.batch_engine import BatchDecisionEngine
from ..service import DecisionService
from .factory import build_flow_service
from .stats import FlowStats

logger = logging.getLogger("agant.import")


class ImportFlowEngine:
    source = Source.LIVE
    kind = "import"

    def __init__(
        self,
        state,
        *,
        transactions: list[Transaction],
        laya_mode: str = "disabled",
        publish: bool = True,
        batch_size: int = 32,
        publish_sample_every: int | None = None,
        decision_mode: str | None = None,
        laya_subfolder: str | None = None,
    ) -> None:
        self.state = state
        self.settings: Settings = state.settings
        self.transactions = transactions
        self.total = len(transactions)
        self.processed = 0
        self.offset = 0
        self.publish = publish
        self.laya_mode = laya_mode or "disabled"
        self.with_laya = self.laya_mode != "disabled"
        self.decision_mode = decision_mode or state.settings.decision_mode
        self.batch_size = max(1, int(batch_size))
        self.publish_mode = "all" if publish else "sampled"
        self.publish_sample_every = int(publish_sample_every or self.settings.publish_sample_every)
        self.process_chunk = 5000
        self.finished = False
        self.started_at: float | None = None
        self._stop = False
        self.error: str | None = None
        self.stats = FlowStats()

        laya_engine = resolve_laya_engine(self.laya_mode, state, subfolder=laya_subfolder)
        self.laya_engine = laya_engine
        if self.batch_size > 1:
            self.batch = BatchDecisionEngine(
                self.settings, state, laya_engine, batch_size=self.batch_size, decision_mode=self.decision_mode
            )
            self.service = DecisionService(state)
            self.laya_active = self.batch.laya_active
        else:
            self.batch = None
            self.service, self.laya_active = build_flow_service(
                self.settings, state, laya_engine, self.decision_mode
            )

    async def run(self) -> None:
        self.started_at = time.perf_counter()
        try:
            logger.info("import iniciado: total=%s batch=%s", self.total, self.batch_size)
            self._emit_status("running")
            index = 0
            while not self._stop and index < self.total:
                chunk = self.transactions[index:index + self.process_chunk]
                results = await asyncio.to_thread(self._decide_block, chunk)
                for transaction, result in zip(chunk, results):
                    self.service.record(result, transaction, Source.LIVE, publish=self.publish)
                    self.stats.note(result)
                index += len(chunk)
                self.processed = index
                self._emit_status("running")
                await asyncio.sleep(0)
            self.finished = True
            self._emit_status("finished")
            logger.info("import finalizado: %s/%s", self.processed, self.total)
        except Exception as exc:  # noqa: BLE001 - se reporta como estado
            self.error = type(exc).__name__
            self.finished = True
            errors = getattr(self.state, "errors", None)
            if errors is not None:
                errors.log(exc, source=Source.LIVE.value, operation="import")
            else:
                logger.error("import falló: %s", exc)
            self._emit_status("error")

    def _decide_block(self, transactions: list[Transaction]) -> list:
        if self.batch is not None:
            return self.batch.decide_block(transactions, Source.LIVE, correlation_id="import")
        return [
            self.service.engine.decide(transaction, source=Source.LIVE, correlation_id="import")
            for transaction in transactions
        ]

    def stop(self) -> None:
        self._stop = True

    @property
    def elapsed_s(self) -> float:
        if self.started_at is None:
            return 0.0
        return time.perf_counter() - self.started_at

    def status_payload(self, state_name: str) -> dict:
        elapsed = self.elapsed_s
        payload = {
            "state": state_name,
            "kind": self.kind,
            "source": self.source.value,
            "laya_mode": self.laya_mode,
            "laya_active": self.laya_active,
            "offset": 0,
            "total": self.total,
            "elapsed_s": elapsed,
            "throughput_tps": self.processed / elapsed if elapsed > 0 else 0.0,
            "error": self.error,
            "batch_mode": self.batch is not None,
            "batch_size": self.batch_size if self.batch is not None else 1,
            "block_size": self.process_chunk,
            "publish_mode": self.publish_mode,
            "decision_mode": self.decision_mode,
        }
        payload.update(self.stats.snapshot())
        return payload

    def _emit_status(self, state_name: str) -> None:
        if not self.publish:
            return
        bus = self.state.bus
        sequence = bus.next_sequence()
        bus.publish(
            Event(
                event_id=f"{self.source.value}:{EventType.FLOW_STATUS.value}:import:{sequence}",
                event_type=EventType.FLOW_STATUS,
                source=self.source,
                sequence=sequence,
                payload=self.status_payload(state_name),
            )
        )

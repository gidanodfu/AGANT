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

"""Flujo Live: transacciones sintéticas server-side con ``source="live"``.

No usa PaySim. Soporta modo per-item y **por lotes** (alto rendimiento).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time

from ..config import Settings
from ..contracts.enums import Decision, EventType, Source
from ..contracts.events import Event
from ..contracts.transaction import Transaction, TransactionType
from ..decision import resolve_laya_engine
from ..decision.batch_engine import BatchDecisionEngine
from ..service import DecisionService
from .factory import build_flow_service
from .stats import FlowStats

logger = logging.getLogger("agant.live")

_TYPES = (
    TransactionType.CASH_OUT,
    TransactionType.PAYMENT,
    TransactionType.CASH_IN,
    TransactionType.TRANSFER,
    TransactionType.DEBIT,
)
_WEIGHTS = (0.35, 0.34, 0.22, 0.08, 0.01)
_MERCHANT_TYPES = {TransactionType.PAYMENT, TransactionType.DEBIT}


class LiveFlowEngine:
    source = Source.LIVE
    kind = "flow"

    def __init__(
        self,
        state,
        *,
        count: int,
        laya_mode: str = "disabled",
        publish: bool | None = None,
        seed: int | None = None,
        batch_size: int = 1,
        block_size: int | None = None,
        publish_mode: str | None = None,
        publish_sample_every: int | None = None,
        laya_subfolder: str | None = None,
        decision_mode: str | None = None,
    ) -> None:
        self.decision_mode = decision_mode or state.settings.decision_mode
        self.state = state
        self.settings: Settings = state.settings
        self.total = int(count)
        self.processed = 0
        self.offset = 0
        self.publish = self.settings.ws_replay if publish is None else publish
        self.laya_mode = laya_mode or "disabled"
        self.with_laya = self.laya_mode != "disabled"
        self.seed = seed
        self.batch_size = max(1, int(batch_size))
        self.block_size = int(block_size or self.settings.block_size)
        self.process_chunk = min(self.block_size, 10_000)
        self.publish_mode = publish_mode or self.settings.publish_mode
        self.publish_sample_every = int(publish_sample_every or self.settings.publish_sample_every)
        self.finished = False
        self.started_at: float | None = None
        self._stop = False
        self.error: str | None = None
        self.stats = FlowStats()

        self.laya_subfolder = laya_subfolder
        laya_engine = resolve_laya_engine(self.laya_mode, state, subfolder=laya_subfolder)
        self.laya_engine = laya_engine
        if self.batch_size > 1:
            self.batch = BatchDecisionEngine(
                self.settings,
                state,
                laya_engine,
                batch_size=self.batch_size,
                decision_mode=self.decision_mode,
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
            rng = random.Random(self.seed)
            logger.info(
                "live flow iniciado: total=%s laya_mode=%s batch=%s",
                self.total,
                self.laya_mode,
                self.batch_size,
            )
            self._emit_status("running")

            index = 0
            while not self._stop and index < self.total:
                size = min(self.process_chunk, self.total - index)
                transactions = [self._synthetic(index + j, rng) for j in range(size)]
                results = await asyncio.to_thread(self._decide_block, transactions)
                for offset, (transaction, result) in enumerate(zip(transactions, results)):
                    publish = self._should_publish(result, index + offset)
                    self.service.record(result, transaction, Source.LIVE, publish=publish)
                    self.stats.note(result)
                index += size
                self.processed = index
                self._emit_status("running")
                await asyncio.sleep(0)

            self.finished = True
            self._emit_status("finished")
            logger.info("live flow finalizado: %s/%s", self.processed, self.total)
        except Exception as exc:  # noqa: BLE001 - se reporta como estado, no se silencia
            self.error = type(exc).__name__
            self.finished = True
            logger.error("live flow falló: %s", exc)
            self._emit_status("error")

    def _synthetic(self, index: int, rng: random.Random) -> Transaction:
        tx_type = rng.choices(_TYPES, weights=_WEIGHTS, k=1)[0]
        amount = round(rng.lognormvariate(7.4, 1.6), 2)
        origin = f"C{rng.randint(1, 50000)}"
        if tx_type in _MERCHANT_TYPES:
            destination = f"M{rng.randint(1, 5000)}"
        else:
            destination = f"C{rng.randint(1, 50000)}"
        return Transaction(
            transaction_id=f"L{index}-{rng.getrandbits(24):06x}",
            step=700 + index // 500,
            type=tx_type,
            amount=amount,
            name_orig=origin,
            old_balance_org=round(amount * rng.uniform(1.0, 5.0), 2),
            name_dest=destination,
            old_balance_dest=round(rng.uniform(0.0, amount), 2),
            is_flagged_fraud=False,
        )

    def _decide_block(self, transactions: list[Transaction]) -> list:
        if self.batch is not None:
            return self.batch.decide_block(transactions, Source.LIVE, correlation_id="live-flow")
        return [
            self.service.engine.decide(transaction, source=Source.LIVE, correlation_id="live-flow")
            for transaction in transactions
        ]

    def _should_publish(self, result, index: int) -> bool:
        if not self.publish:
            return False
        if self.publish_mode == "all":
            return True
        if result.final_decision in (Decision.FRAUD, Decision.SUSPICIOUS) or result.laya.invoked:
            return True
        return index % self.publish_sample_every == 0

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
            "block_size": self.block_size,
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
                event_id=f"{self.source.value}:{EventType.FLOW_STATUS.value}:flow:{sequence}",
                event_type=EventType.FLOW_STATUS,
                source=self.source,
                sequence=sequence,
                payload=self.status_payload(state_name),
            )
        )

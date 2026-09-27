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

"""Motor de replay: recorre PaySim en orden temporal y decide (source=replay).

Soporta dos caminos con la misma semántica de decisión:
- **per-item** (online, batch_size=1), y
- **por lotes** (alto rendimiento), con ML vectorizado en lotes de
  ``batch_size`` y publicación de eventos muestreada o completa.
"""

from __future__ import annotations

import asyncio
import logging
import time

from ..config import Settings
from ..contracts.enums import Decision, EventType, Source
from ..contracts.events import Event
from ..contracts.transaction import Transaction
from ..data.paysim_db import connect
from ..decision import resolve_laya_engine
from ..decision.batch_engine import BatchDecisionEngine
from ..service import DecisionService
from .factory import build_flow_service
from .stats import FlowStats

logger = logging.getLogger("agant.replay")

_QUERY = (
    "SELECT row_id, step, type, amount, nameOrig, oldbalanceOrg, "
    "nameDest, oldbalanceDest, isFlaggedFraud FROM transactions ORDER BY row_id"
)


class ReplayEngine:
    source = Source.REPLAY
    kind = "flow"

    def __init__(
        self,
        state,
        *,
        with_laya: bool = False,
        max_records: int | None = None,
        offset: int = 0,
        publish: bool | None = None,
        laya_mode: str | None = None,
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
        self.max_records = max_records
        self.offset = max(0, int(offset))
        self.publish = self.settings.ws_replay if publish is None else publish
        self.laya_mode = laya_mode or ("pretrained" if with_laya else "disabled")
        self.with_laya = self.laya_mode != "disabled"
        self.batch_size = max(1, int(batch_size))
        self.block_size = int(block_size or self.settings.block_size)
        # Memoria acotada: se procesa en sub-trozos aunque el bloque sea grande.
        self.process_chunk = min(self.block_size, 10_000)
        self.publish_mode = publish_mode or self.settings.publish_mode
        self.publish_sample_every = int(publish_sample_every or self.settings.publish_sample_every)
        self.processed = 0
        self.total = 0
        self.finished = False
        self.started_at: float | None = None
        self._stop = False
        self.error: str | None = None
        self.stats = FlowStats()

        try:
            self.total = int(
                connect(self.settings)
                .execute(f"SELECT count(*) FROM ({self._build_query()})")
                .fetchone()[0]
            )
        except Exception:  # noqa: BLE001 - se recalcula en run()
            self.total = 0

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
            conn = connect(self.settings)
            query = self._build_query()
            self.total = int(conn.execute(f"SELECT count(*) FROM ({query})").fetchone()[0])
            logger.info(
                "replay iniciado: laya_mode=%s batch=%s block=%s offset=%s total=%s",
                self.laya_mode,
                self.batch_size,
                self.block_size,
                self.offset,
                self.total,
            )
            self._emit_status("running")

            cursor = conn.execute(query)
            while not self._stop:
                rows = cursor.fetchmany(self.process_chunk)
                if not rows:
                    break
                transactions = self._rows_to_transactions(rows)
                results = await asyncio.to_thread(self._decide_block, transactions)
                for index, (transaction, result) in enumerate(zip(transactions, results)):
                    publish = self._should_publish(result, self.processed + index)
                    self.service.record(result, transaction, Source.REPLAY, publish=publish)
                    self.stats.note(result)
                self.processed += len(results)
                self._emit_status("running")
                await asyncio.sleep(0)
            self.finished = True
            self._emit_status("finished")
            logger.info("replay finalizado: %s/%s", self.processed, self.total)
        except Exception as exc:  # noqa: BLE001 - se reporta como estado, no se silencia
            self.error = type(exc).__name__
            self.finished = True
            logger.error("replay falló: %s", exc)
            self._emit_status("error")

    def _build_query(self) -> str:
        limit = f"LIMIT {int(self.max_records)}" if self.max_records else "LIMIT 1000000000"
        offset = f" OFFSET {self.offset}" if self.offset else ""
        return f"{_QUERY} {limit}{offset}"

    def _rows_to_transactions(self, rows) -> list[Transaction]:
        return [
            Transaction(
                transaction_id=f"R{row[0]}",
                step=int(row[1]),
                type=row[2],
                amount=float(row[3]),
                name_orig=row[4],
                old_balance_org=float(row[5]),
                name_dest=row[6],
                old_balance_dest=float(row[7]),
                is_flagged_fraud=bool(row[8]),
            )
            for row in rows
        ]

    def _decide_block(self, transactions: list[Transaction]) -> list:
        if self.batch is not None:
            return self.batch.decide_block(transactions, Source.REPLAY, correlation_id="replay")
        return [
            self.service.engine.decide(transaction, source=Source.REPLAY, correlation_id="replay")
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
            "offset": self.offset,
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

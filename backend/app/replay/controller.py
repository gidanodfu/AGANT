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

"""Control de flujos (replay PaySim o live sintético) como tarea de fondo."""

from __future__ import annotations

import asyncio
from functools import partial

from ..contracts.enums import Source
from ..errors import ReplayError
from .engine import ReplayEngine
from .import_flow import ImportFlowEngine
from .live_flow import LiveFlowEngine

_IDLE = {
    "state": "idle",
    "kind": None,
    "source": None,
    "processed": 0,
    "total": 0,
    "fraud": 0,
    "suspicious": 0,
    "legitimate": 0,
    "errors": 0,
    "laya_invocations": 0,
    "latency_p95_ms": 0.0,
    "throughput_tps": 0.0,
    "elapsed_s": 0.0,
    "with_laya": False,
    "laya_mode": "disabled",
    "laya_active": False,
    "error": None,
    "batch_mode": False,
    "batch_size": 1,
    "block_size": 0,
    "publish_mode": "sampled",
}


class ReplayController:
    def __init__(self, state) -> None:
        self.state = state
        self.engine: ReplayEngine | LiveFlowEngine | None = None
        self._task: asyncio.Task | None = None

    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(
        self,
        *,
        with_laya: bool = False,
        max_records: int | None = None,
        offset: int = 0,
        publish: bool | None = None,
    ) -> dict:
        if not self.state.settings.paysim_csv.exists():
            raise ReplayError("no hay dataset PaySim disponible para replay")
        publish = self.state.settings.ws_replay if publish is None else publish
        engine = await asyncio.to_thread(
            partial(
                ReplayEngine,
                self.state,
                with_laya=with_laya,
                max_records=max_records,
                offset=offset,
                publish=publish,
            )
        )
        return self._launch(engine)

    async def start_flow(
        self,
        *,
        source: str,
        count: int | None,
        offset: int = 0,
        laya_mode: str = "disabled",
        publish: bool = True,
        batch_size: int = 1,
        block_size: int | None = None,
        publish_mode: str | None = None,
        laya_subfolder: str | None = None,
        decision_mode: str | None = None,
    ) -> dict:
        common = dict(
            laya_mode=laya_mode,
            publish=publish,
            batch_size=batch_size,
            block_size=block_size,
            publish_mode=publish_mode,
            laya_subfolder=laya_subfolder,
            decision_mode=decision_mode,
        )
        if source == "live":
            if not count:
                raise ReplayError("la fuente Live requiere una cantidad")
            factory = partial(LiveFlowEngine, self.state, count=count, **common)
        elif source == "replay":
            if not self.state.settings.paysim_csv.exists():
                raise ReplayError("no hay dataset PaySim disponible para replay")
            # count None => todo el dataset
            factory = partial(ReplayEngine, self.state, max_records=count, offset=offset, **common)
        else:
            raise ReplayError(f"fuente de flujo inválida: {source!r}")
        # La construcción (posible carga de checkpoint custom) no debe bloquear
        # el event loop; la UI muestra "Cargando…" mientras tanto.
        engine = await asyncio.to_thread(factory)
        return self._launch(engine)

    async def start_import(
        self,
        *,
        transactions: list,
        laya_mode: str = "disabled",
        batch_size: int = 32,
        decision_mode: str | None = None,
        laya_subfolder: str | None = None,
    ) -> dict:
        factory = partial(
            ImportFlowEngine,
            self.state,
            transactions=transactions,
            laya_mode=laya_mode,
            publish=True,
            batch_size=batch_size,
            decision_mode=decision_mode,
            laya_subfolder=laya_subfolder,
        )
        engine = await asyncio.to_thread(factory)
        return self._launch(engine)

    def _launch(self, engine) -> dict:
        if self.running():
            raise ReplayError("ya hay un flujo en curso")
        if engine.source is Source.REPLAY:
            self.state.metrics.reset_source(Source.REPLAY)
        self.engine = engine
        self._task = asyncio.create_task(engine.run())
        return self.status()

    async def stop(self) -> dict:
        if self.engine is not None:
            self.engine.stop()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=15)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        self._task = None
        return self.status()

    def status(self) -> dict:
        if self.engine is None:
            return dict(_IDLE)
        if self.running():
            state_name = "running"
        elif self.engine.finished:
            state_name = "finished"
        else:
            state_name = "stopped"
        payload = self.engine.status_payload(state_name)
        payload["with_laya"] = self.engine.with_laya
        return payload

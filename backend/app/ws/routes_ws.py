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

"""WebSocket para eventos dinámicos y SSE para métricas agregadas."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ..api.deps import get_state
from ..contracts.enums import EventType

logger = logging.getLogger("agant.ws")

router = APIRouter(tags=["realtime"])

_TRANSACTION_TYPES = {
    EventType.TRANSACTION_CREATED,
    EventType.TRANSACTION_UPDATED,
    EventType.DECISION_CREATED,
    EventType.LAYA_DECISION,
}


def _origin_allowed(websocket: WebSocket, allowed: list[str]) -> bool:
    if not allowed:
        return True
    return websocket.headers.get("origin") in allowed


async def _stream(websocket: WebSocket, allowed_types: set[EventType] | None) -> None:
    state = websocket.app.state.services
    if not _origin_allowed(websocket, state.settings.allowed_ws_origin_list):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    queue = state.bus.subscribe()
    state.ws_clients += 1
    try:
        while True:
            event = await queue.get()
            if allowed_types is None or event.event_type in allowed_types:
                await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 - cierre controlado, se registra
        logger.warning("WS cerrado: %s", type(exc).__name__)
    finally:
        state.bus.unsubscribe(queue)
        state.ws_clients = max(0, state.ws_clients - 1)


@router.websocket("/api/v1/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await _stream(websocket, None)


@router.websocket("/api/v1/ws/transactions")
async def ws_transactions(websocket: WebSocket) -> None:
    await _stream(websocket, _TRANSACTION_TYPES)


@router.get("/api/v1/metrics/stream")
async def metrics_stream(request: Request) -> StreamingResponse:
    state = get_state(request)

    async def generator():
        while True:
            if await request.is_disconnected():
                break
            data = state.metrics.snapshot_payload(
                bus_stats=state.bus.stats(), ws_clients=state.ws_clients
            )
            yield f"event: metrics.updated\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

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

"""Endpoints de flujo controlados por la interfaz.

Permiten iniciar/detener un flujo Live (sintético, ``source=live_synthetic``) o
un replay de PaySim (``source=replay``). Si ``AGANT_ADMIN_TOKEN`` está
configurado, exigen ``X-Admin-Token``; con token vacío quedan abiertos para no
romper el panel en desarrollo.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator

from ..contracts import ApiResponse
from ..errors import ReplayError
from .deps import get_state, require_admin_optional
from .rate_limit import rate_limit_flow

router = APIRouter(prefix="/api/v1/flow", tags=["flow"])

MAX_FLOW = 100_000


class FlowRequest(BaseModel):
    source: Literal["live", "replay"] = "live"
    count: int | Literal["all"] = 1000
    offset: int = Field(default=0, ge=0)
    laya_mode: Literal["disabled", "pretrained", "custom"] = "disabled"
    laya_subfolder: str | None = None
    decision_mode: Literal["hybrid", "laya_all"] | None = None
    batch_size: Literal[1, 32, 64] = 1
    block_size: int | None = Field(default=None, ge=1, le=1_000_000)
    publish_mode: Literal["sampled", "all"] | None = None

    @model_validator(mode="after")
    def _check_count(self) -> "FlowRequest":
        if self.count != "all" and (not isinstance(self.count, int) or self.count < 1 or self.count > MAX_FLOW):
            raise ValueError(f"count debe ser 'all' o un entero entre 1 y {MAX_FLOW}")
        return self


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.post(
    "/start",
    response_model=ApiResponse[dict],
    dependencies=[Depends(rate_limit_flow), Depends(require_admin_optional)],
)
async def start(request: Request, body: FlowRequest) -> ApiResponse[dict]:
    state = get_state(request)
    if state.replay is None:
        raise ReplayError("control de flujo no disponible")
    data = await state.replay.start_flow(
        source=body.source,
        count=None if body.count == "all" else body.count,
        offset=body.offset,
        laya_mode=body.laya_mode,
        publish=True,
        batch_size=body.batch_size,
        block_size=body.block_size,
        publish_mode=body.publish_mode,
        laya_subfolder=body.laya_subfolder,
        decision_mode=body.decision_mode,
    )
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.post(
    "/stop", response_model=ApiResponse[dict], dependencies=[Depends(require_admin_optional)]
)
async def stop(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    if state.replay is None:
        raise ReplayError("control de flujo no disponible")
    data = await state.replay.stop()
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.get("/status", response_model=ApiResponse[dict])
async def status(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    data = state.replay.status() if state.replay else {"state": "unavailable"}
    return ApiResponse.ok(data, request_id=_request_id(request))

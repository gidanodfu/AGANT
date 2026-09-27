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

"""Endpoints de replay (inicio/parada administrativos)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..contracts import ApiResponse
from ..errors import ReplayError
from .deps import get_state, require_admin

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


class ReplayRequest(BaseModel):
    with_laya: bool = False
    max_records: int | None = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.post("/start", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def start(request: Request, body: ReplayRequest) -> ApiResponse[dict]:
    state = get_state(request)
    if state.replay is None:
        raise ReplayError("replay no disponible")
    data = await state.replay.start(
        with_laya=body.with_laya, max_records=body.max_records, offset=body.offset
    )
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.post("/stop", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def stop(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    if state.replay is None:
        raise ReplayError("replay no disponible")
    data = await state.replay.stop()
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.get("/status", response_model=ApiResponse[dict])
async def status(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    data = state.replay.status() if state.replay else {"state": "unavailable"}
    return ApiResponse.ok(data, request_id=_request_id(request))

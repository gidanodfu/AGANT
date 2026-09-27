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

"""Endpoint de drift temporal (offline, separado de LIVE)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..contracts import ApiResponse
from ..observability.drift import drift_report
from .deps import get_state

router = APIRouter(prefix="/api/v1", tags=["drift"])


@router.get("/drift", response_model=ApiResponse[dict])
async def drift(request: Request, sample: int = Query(default=50_000, ge=1000, le=500_000)) -> ApiResponse[dict]:
    state = get_state(request)
    try:
        data = drift_report(state.settings, sample=sample)
    except FileNotFoundError:
        data = {"available": False, "reason": "features no generadas"}
    if state.live_drift is not None:
        data = {**data, "live": state.live_drift.snapshot()}
    return ApiResponse.ok(data, request_id=getattr(request.state, "request_id", "-"))

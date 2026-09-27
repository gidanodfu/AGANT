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

"""Endpoints de estado, transacciones, decisiones de Laya y métricas."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..contracts import ApiResponse, Source
from ..service import DecisionService
from .deps import get_state

router = APIRouter(prefix="/api/v1", tags=["observability"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("/system/status", response_model=ApiResponse[dict])
async def system_status(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    report = state.startup_report
    data = {
        "summary": report.summary() if report else "AGANT STARTING",
        "components": report.component_status() if report else {},
        "decision_mode": state.settings.decision_mode,
        "laya_mode": state.settings.laya_mode,
        "laya_status": getattr(state.laya, "status", None).value if state.laya else "disabled",
        "laya_custom_available": state.settings.laya_custom_available,
        "laya_custom_subfolder": state.settings.laya_custom_subfolder,
        "laya_subfolders": state.settings.laya_subfolder_list,
    }
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.get("/transactions", response_model=ApiResponse[list])
async def transactions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    source: Source | None = Query(default=None),
) -> ApiResponse[list]:
    state = get_state(request)
    data = state.store.recent_transactions(limit, source)
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.get("/decisions", response_model=ApiResponse[list])
async def decisions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    source: Source | None = Query(default=None),
) -> ApiResponse[list]:
    state = get_state(request)
    data = state.store.recent_decisions(limit, source)
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.get("/laya-decisions", response_model=ApiResponse[list])
async def laya_decisions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> ApiResponse[list]:
    state = get_state(request)
    data = state.store.recent_laya_decisions(limit)
    return ApiResponse.ok(data, request_id=_request_id(request))


@router.get("/metrics", response_model=ApiResponse[dict])
async def metrics(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    data = state.metrics.snapshot_payload(
        bus_stats=state.bus.stats(), ws_clients=state.ws_clients
    )
    return ApiResponse.ok(data, request_id=_request_id(request))

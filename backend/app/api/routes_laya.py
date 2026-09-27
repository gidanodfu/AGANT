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

"""Panel visual de Laya: estado, carga de checkpoint y prueba."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..contracts import ApiResponse, Decision, Evidence, GraphContext, Source, Transaction
from ..decision.laya_engine import LayaDecisionEngine, resolve_laya_engine
from ..decision.state_builder import DecisionStateBuilder
from ..features.feature_builder import FeatureBuilder
from .deps import get_state
from .rate_limit import rate_limit_flow

router = APIRouter(prefix="/api/v1/laya", tags=["laya"])


def _vram() -> dict:
    try:
        import torch

        if torch.cuda.is_available():
            return {
                "allocated_mb": torch.cuda.memory_allocated() / 1e6,
                "reserved_mb": torch.cuda.memory_reserved() / 1e6,
                "device": torch.cuda.get_device_name(0),
            }
    except Exception:  # noqa: BLE001 - opcional
        pass
    return {"available": False}


@router.get("/status", response_model=ApiResponse[dict])
async def status(request: Request) -> ApiResponse[dict]:
    state = get_state(request)
    laya = state.laya
    payload = {
        "mode": getattr(laya, "mode", state.settings.laya_mode),
        "status": getattr(getattr(laya, "status", None), "value", "disabled"),
        "subfolder": state.settings.laya_active_subfolder,
        "subfolders": state.settings.laya_subfolder_list,
        "load_error": getattr(laya, "load_error", None),
        "decision_mode": state.settings.decision_mode,
        "vram": _vram(),
    }
    return ApiResponse.ok(payload, request_id=getattr(request.state, "request_id", "-"))


class LayaLoadRequest(BaseModel):
    mode: Literal["disabled", "pretrained", "custom"] = "pretrained"
    subfolder: str | None = None
    warmup: bool = True


@router.post("/load", response_model=ApiResponse[dict], dependencies=[Depends(rate_limit_flow)])
async def load(request: Request, body: LayaLoadRequest) -> ApiResponse[dict]:
    state = get_state(request)
    settings = state.settings

    def _build() -> LayaDecisionEngine:
        if body.mode == "disabled":
            return LayaDecisionEngine(
                settings.model_copy(update={"laya_enabled": False, "laya_mode": "disabled"})
            )
        return resolve_laya_engine(body.mode, state, subfolder=body.subfolder)

    engine = await asyncio.to_thread(_build)
    # El motor pasa a ser el usado por la ruta global /decision y los flujos.
    state.laya = engine
    if getattr(state, "decision_engine", None) is not None:
        state.decision_engine.laya_engine = engine
    data = {
        "mode": engine.mode,
        "status": engine.status.value,
        "laya_active": engine.enabled and engine.status.value == "ready",
        "load_error": engine.load_error,
        "vram": _vram(),
    }
    return ApiResponse.ok(data, request_id=getattr(request.state, "request_id", "-"))


class LayaTestRequest(BaseModel):
    transaction: Transaction | None = None


@router.post("/test", response_model=ApiResponse[dict])
async def test(request: Request, body: LayaTestRequest | None = None) -> ApiResponse[dict]:
    state = get_state(request)
    laya = state.laya
    transaction = (body.transaction if body else None) or Transaction(
        transaction_id="laya-test",
        step=700,
        type="TRANSFER",
        amount=181.0,
        name_orig="C1",
        old_balance_org=181.0,
        name_dest="C2",
        old_balance_dest=0.0,
    )
    features = FeatureBuilder().build(transaction, GraphContext())
    decision_state = DecisionStateBuilder(state.settings).build(
        transaction_id=transaction.transaction_id,
        source=Source.LIVE,
        correlation_id="laya-test",
        features=features,
        evidence=Evidence(),
    )
    result = await asyncio.to_thread(
        lambda: laya.evaluate(decision_state, Decision.SUSPICIOUS, decide_all=True)
    )
    return ApiResponse.ok(result.model_dump(mode="json"), request_id=getattr(request.state, "request_id", "-"))

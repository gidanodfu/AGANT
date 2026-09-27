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

"""Endpoints de decisión online y por lote."""

from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from ..contracts import ApiResponse, Source, Transaction
from ..errors import ValidationError
from ..service import DecisionService
from .deps import get_service
from .rate_limit import rate_limit_decision

router = APIRouter(prefix="/api/v1", tags=["decision"], dependencies=[Depends(rate_limit_decision)])

MAX_BATCH = 1000


@router.post("/decision", response_model=ApiResponse[dict])
async def decide(
    request: Request,
    transaction: Transaction,
    decision_mode: Literal["hybrid", "laya_all"] | None = Query(default=None),
    service: DecisionService = Depends(get_service),
) -> ApiResponse[dict]:
    result = await service.process(
        transaction,
        source=Source.LIVE,
        correlation_id=_request_id(request),
        decision_mode=decision_mode,
    )
    return ApiResponse.ok(_serialize(result), request_id=_request_id(request))


@router.post("/decision/batch", response_model=ApiResponse[list])
async def decide_batch(
    request: Request,
    transactions: list[Transaction],
    service: DecisionService = Depends(get_service),
) -> ApiResponse[list]:
    if not transactions:
        raise ValidationError("el lote no puede estar vacío")
    if len(transactions) > MAX_BATCH:
        raise ValidationError(f"el lote excede el máximo de {MAX_BATCH} transacciones")

    results = []
    for transaction in transactions:
        result = await service.process(
            transaction, source=Source.LIVE, correlation_id=_request_id(request)
        )
        results.append(_serialize(result))
    return ApiResponse.ok(results, request_id=_request_id(request))


def _serialize(result) -> dict:
    start = time.perf_counter()
    payload = result.model_dump(mode="json")
    payload["latency"]["serialization_ms"] = round((time.perf_counter() - start) * 1000.0, 4)
    return payload


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")

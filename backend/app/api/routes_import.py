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

"""Importación de transacciones provistas por el usuario (procesadas en vivo)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..contracts import ApiResponse, Transaction
from ..errors import ReplayError
from .deps import get_state, require_admin_optional
from .rate_limit import rate_limit_flow

router = APIRouter(prefix="/api/v1", tags=["import"])

MAX_IMPORT = 20_000


class ImportRequest(BaseModel):
    transactions: list[Transaction] = Field(min_length=1, max_length=MAX_IMPORT)
    laya_mode: Literal["disabled", "pretrained", "custom"] = "disabled"
    laya_subfolder: str | None = None
    decision_mode: Literal["hybrid", "laya_all"] | None = None
    batch_size: Literal[1, 32, 64] = 32


@router.post(
    "/transactions/import",
    response_model=ApiResponse[dict],
    dependencies=[Depends(rate_limit_flow), Depends(require_admin_optional)],
)
async def import_transactions(request: Request, body: ImportRequest) -> ApiResponse[dict]:
    state = get_state(request)
    if state.replay is None:
        raise ReplayError("control de flujo no disponible")
    data = await state.replay.start_import(
        transactions=body.transactions,
        laya_mode=body.laya_mode,
        batch_size=body.batch_size,
        decision_mode=body.decision_mode,
        laya_subfolder=body.laya_subfolder,
    )
    return ApiResponse.ok(data, request_id=getattr(request.state, "request_id", "-"))

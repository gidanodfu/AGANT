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

"""Dependencias de FastAPI para acceder al estado de la aplicación."""

from __future__ import annotations

from fastapi import Request

from ..contracts.enums import ErrorCode, Severity
from ..errors import AGANTError
from ..service import DecisionService
from .state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_service(request: Request) -> DecisionService:
    return request.app.state.decision_service


def require_admin(request: Request) -> None:
    """Protege endpoints administrativos; si no hay token, no se exponen."""
    token = request.app.state.settings.admin_token
    if not token:
        raise AGANTError(
            "administración deshabilitada: falta AGANT_ADMIN_TOKEN",
            code=ErrorCode.VALIDATION_ERROR,
            status=403,
            severity=Severity.WARNING,
        )
    provided = request.headers.get("X-Admin-Token")
    if provided != token:
        raise AGANTError(
            "credencial administrativa inválida",
            code=ErrorCode.VALIDATION_ERROR,
            status=401,
            severity=Severity.WARNING,
        )

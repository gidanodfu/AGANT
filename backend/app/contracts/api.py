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

"""Contratos de respuesta de la API y de error seguro."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .enums import ErrorCode, Severity

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Error expuesto al cliente. Nunca contiene trazas, rutas ni secretos."""

    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    severity: Severity = Severity.RECOVERABLE
    source: str | None = None
    operation: str | None = None
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Envoltura de respuesta uniforme: ``success``, ``data``, ``error``, ``request_id``."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    data: T | None = None
    error: ErrorResponse | None = None
    request_id: str = Field(min_length=1)

    @classmethod
    def ok(cls, data: T, request_id: str) -> "ApiResponse[T]":
        return cls(success=True, data=data, error=None, request_id=request_id)

    @classmethod
    def fail(cls, error: ErrorResponse, request_id: str) -> "ApiResponse[T]":
        return cls(success=False, data=None, error=error, request_id=request_id)

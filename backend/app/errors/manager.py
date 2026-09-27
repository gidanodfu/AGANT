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

"""Gestión explícita de errores: clasificar, registrar, medir y responder.

Ningún error se silencia. Los mensajes expuestos al cliente son seguros;
el detalle técnico queda únicamente en los logs del servidor.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..contracts.api import ErrorResponse
from ..contracts.enums import ErrorCode, Severity
from .taxonomy import AGANTError, ValidationError

logger = logging.getLogger("agant.errors")


class ErrorManager:
    """Clasifica excepciones y produce respuestas seguras y trazables."""

    def __init__(self, metrics: Any | None = None) -> None:
        self.metrics = metrics

    def classify(self, exc: BaseException) -> AGANTError:
        if isinstance(exc, AGANTError):
            return exc
        if isinstance(exc, PydanticValidationError):
            return ValidationError("validación de entrada", details={"errors": exc.error_count()})
        if isinstance(exc, TimeoutError):
            return AGANTError(str(exc) or "timeout", code=ErrorCode.TIMEOUT_ERROR)
        return AGANTError("error interno no clasificado", code=ErrorCode.INTERNAL_ERROR)

    def error_response(
        self,
        exc: BaseException,
        *,
        source: str | None = None,
        operation: str | None = None,
    ) -> ErrorResponse:
        error = self.classify(exc)
        return ErrorResponse(
            code=error.code,
            message=error.public_message or error.safe_message,
            severity=error.severity,
            source=source or error.source,
            operation=operation or error.operation,
            details=error.details or None,
        )

    def log(
        self,
        exc: BaseException,
        *,
        request_id: str | None = None,
        transaction_id: str | None = None,
        source: str | None = None,
        operation: str | None = None,
    ) -> AGANTError:
        error = self.classify(exc)
        logger.error(
            "error code=%s severity=%s source=%s operation=%s request_id=%s tx=%s detail=%s",
            error.code.value,
            error.severity.value,
            source or error.source or "-",
            operation or error.operation or "-",
            request_id or "-",
            transaction_id or "-",
            str(exc),
            exc_info=not isinstance(exc, AGANTError),
        )
        self._record(error.severity)
        return error

    def _record(self, severity: Severity) -> None:
        if self.metrics is None:
            return
        record = getattr(self.metrics, "record_error", None)
        if record is not None:
            record(severity.value)

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

"""Taxonomía de errores de AGANT y excepción base tipada.

Cada error lleva ``code``, ``status`` HTTP sugerido, ``severity``,
``source``, ``operation`` y ``details`` seguros (sin secretos ni rutas).
"""

from __future__ import annotations

from typing import Any

from ..contracts.enums import ErrorCode, Severity

HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.CONFIG_ERROR: 500,
    ErrorCode.FEATURE_ERROR: 500,
    ErrorCode.GRAPH_ERROR: 503,
    ErrorCode.ML_ERROR: 503,
    ErrorCode.MODEL_LOAD_ERROR: 503,
    ErrorCode.LAYA_ERROR: 503,
    ErrorCode.DATABASE_ERROR: 503,
    ErrorCode.EVENT_BUS_ERROR: 500,
    ErrorCode.WEBSOCKET_ERROR: 500,
    ErrorCode.SSE_ERROR: 500,
    ErrorCode.REPLAY_ERROR: 409,
    ErrorCode.TIMEOUT_ERROR: 504,
    ErrorCode.INTERNAL_ERROR: 500,
}

DEFAULT_SEVERITY: dict[ErrorCode, Severity] = {
    ErrorCode.VALIDATION_ERROR: Severity.WARNING,
    ErrorCode.CONFIG_ERROR: Severity.CRITICAL,
    ErrorCode.FEATURE_ERROR: Severity.RECOVERABLE,
    ErrorCode.GRAPH_ERROR: Severity.UNAVAILABLE,
    ErrorCode.ML_ERROR: Severity.UNAVAILABLE,
    ErrorCode.MODEL_LOAD_ERROR: Severity.UNAVAILABLE,
    ErrorCode.LAYA_ERROR: Severity.RECOVERABLE,
    ErrorCode.DATABASE_ERROR: Severity.UNAVAILABLE,
    ErrorCode.EVENT_BUS_ERROR: Severity.RECOVERABLE,
    ErrorCode.WEBSOCKET_ERROR: Severity.WARNING,
    ErrorCode.SSE_ERROR: Severity.WARNING,
    ErrorCode.REPLAY_ERROR: Severity.RECOVERABLE,
    ErrorCode.TIMEOUT_ERROR: Severity.RECOVERABLE,
    ErrorCode.INTERNAL_ERROR: Severity.CRITICAL,
}

SAFE_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "La transacción enviada no es válida.",
    ErrorCode.CONFIG_ERROR: "La configuración del servicio es inválida.",
    ErrorCode.FEATURE_ERROR: "No fue posible construir las características de la transacción.",
    ErrorCode.GRAPH_ERROR: "El contexto de grafo no está disponible.",
    ErrorCode.ML_ERROR: "El modelo de Machine Learning no está disponible.",
    ErrorCode.MODEL_LOAD_ERROR: "No fue posible cargar el modelo requerido.",
    ErrorCode.LAYA_ERROR: "No fue posible completar la evaluación de Laya.",
    ErrorCode.DATABASE_ERROR: "El almacenamiento de datos no está disponible.",
    ErrorCode.EVENT_BUS_ERROR: "No fue posible publicar el evento interno.",
    ErrorCode.WEBSOCKET_ERROR: "La conexión en tiempo real presentó un problema.",
    ErrorCode.SSE_ERROR: "El canal de métricas presentó un problema.",
    ErrorCode.REPLAY_ERROR: "La operación de replay no pudo completarse.",
    ErrorCode.TIMEOUT_ERROR: "La operación excedió el tiempo máximo permitido.",
    ErrorCode.INTERNAL_ERROR: "Ocurrió un error interno controlado.",
}


class AGANTError(Exception):
    """Excepción base de AGANT, con metadatos operativos seguros."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status: int | None = None,
        severity: Severity | None = None,
        source: str | None = None,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
        public_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        # Mensaje seguro específico (provisto por el desarrollador). Si no
        # existe, se usa el mensaje genérico del código.
        self.public_message = public_message
        self.status = status if status is not None else HTTP_STATUS.get(code, 500)
        self.severity = severity if severity is not None else DEFAULT_SEVERITY.get(
            code, Severity.CRITICAL
        )
        self.source = source
        self.operation = operation
        self.details = details or {}

    @property
    def safe_message(self) -> str:
        return SAFE_MESSAGES.get(self.code, SAFE_MESSAGES[ErrorCode.INTERNAL_ERROR])


class ValidationError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.VALIDATION_ERROR)
        super().__init__(message, **kw)


class FeatureError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.FEATURE_ERROR)
        super().__init__(message, **kw)


class GraphError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.GRAPH_ERROR)
        super().__init__(message, **kw)


class MLError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.ML_ERROR)
        super().__init__(message, **kw)


class LayaError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.LAYA_ERROR)
        super().__init__(message, **kw)


class ModelLoadError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.MODEL_LOAD_ERROR)
        super().__init__(message, **kw)


class ConfigError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.CONFIG_ERROR)
        super().__init__(message, **kw)


class ReplayError(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.REPLAY_ERROR)
        super().__init__(message, **kw)


class TimeoutError_(AGANTError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("code", ErrorCode.TIMEOUT_ERROR)
        super().__init__(message, **kw)

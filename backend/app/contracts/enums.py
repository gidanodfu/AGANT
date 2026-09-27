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

"""Enumeraciones compartidas por los contratos de AGANT."""

from __future__ import annotations

from enum import Enum, IntEnum


class Decision(str, Enum):
    FRAUD = "FRAUD"
    SUSPICIOUS = "SUSPICIOUS"
    LEGITIMATE = "LEGITIMATE"


class Source(str, Enum):
    LIVE = "live"
    REPLAY = "replay"


class ComponentStatus(str, Enum):
    DISABLED = "disabled"
    LOADING = "loading"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class LayaStatus(str, Enum):
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"
    INVOKED = "invoked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class FallbackLevel(IntEnum):
    GRAPH_ML = 0
    ML_ONLY = 1
    RULES_ONLY = 2


class Severity(str, Enum):
    WARNING = "warning"
    RECOVERABLE = "recoverable"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FEATURE_ERROR = "FEATURE_ERROR"
    GRAPH_ERROR = "GRAPH_ERROR"
    ML_ERROR = "ML_ERROR"
    LAYA_ERROR = "LAYA_ERROR"
    MODEL_LOAD_ERROR = "MODEL_LOAD_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EVENT_BUS_ERROR = "EVENT_BUS_ERROR"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    SSE_ERROR = "SSE_ERROR"
    REPLAY_ERROR = "REPLAY_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EventType(str, Enum):
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    DECISION_CREATED = "decision.created"
    LAYA_DECISION = "laya.decision"
    SYSTEM_STATUS = "system.status"
    SYSTEM_ERROR = "system.error"
    REPLAY_STATUS = "replay.status"
    FLOW_STATUS = "flow.status"
    METRICS_UPDATED = "metrics.updated"


class ConnectionState(str, Enum):
    LOADING = "loading"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    DEGRADED = "degraded"
    READY = "ready"

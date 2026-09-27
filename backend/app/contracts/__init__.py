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

"""Contratos tipados de AGANT (única superficie de tipos entre módulos)."""

from .api import ApiResponse, ErrorResponse
from .decision import DecisionResult, DecisionState, LatencyBreakdown, LayaResult
from .enums import (
    ComponentStatus,
    ConnectionState,
    Decision,
    ErrorCode,
    EventType,
    FallbackLevel,
    LayaStatus,
    Severity,
    Source,
)
from .events import Event, build_event_id
from .evidence import Evidence, GraphAvailability, MLResult, RuleResult
from .metrics import MetricSnapshot, ModelMetrics, Percentiles
from .transaction import (
    GRAPH_FEATURE_NAMES,
    ML_FEATURE_NAMES,
    MODEL_FEATURE_NAMES,
    GraphContext,
    InferenceFeatures,
    Transaction,
    TransactionType,
)

__all__ = [
    "ApiResponse",
    "ErrorResponse",
    "DecisionResult",
    "DecisionState",
    "LatencyBreakdown",
    "LayaResult",
    "ComponentStatus",
    "ConnectionState",
    "Decision",
    "ErrorCode",
    "EventType",
    "FallbackLevel",
    "LayaStatus",
    "Severity",
    "Source",
    "Event",
    "build_event_id",
    "Evidence",
    "GraphAvailability",
    "MLResult",
    "RuleResult",
    "MetricSnapshot",
    "ModelMetrics",
    "Percentiles",
    "GRAPH_FEATURE_NAMES",
    "ML_FEATURE_NAMES",
    "MODEL_FEATURE_NAMES",
    "GraphContext",
    "InferenceFeatures",
    "Transaction",
    "TransactionType",
]

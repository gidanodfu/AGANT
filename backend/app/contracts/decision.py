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

"""Contratos de estado de decisión, resultado de Laya y decisión final.

Se preserva la separación estricta entre ``primary_decision``,
``primary_score``, ``laya_result``, ``final_decision`` y
``fallback_reason``. Un upgrade/downgrade de Laya nunca sobrescribe la
decisión primaria de forma silenciosa.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from .enums import Decision, FallbackLevel, LayaStatus, Source
from .evidence import Evidence
from .transaction import InferenceFeatures, Transaction


class LatencyBreakdown(BaseModel):
    """Desglose de latencia por etapa, en milisegundos."""

    model_config = ConfigDict(extra="forbid")

    parsing_ms: float = 0.0
    validation_ms: float = 0.0
    features_ms: float = 0.0
    graph_ms: float = 0.0
    rules_ms: float = 0.0
    ml_ms: float = 0.0
    state_ms: float = 0.0
    laya_ms: float = 0.0
    fallback_ms: float = 0.0
    serialization_ms: float = 0.0
    event_ms: float = 0.0
    total_ms: float = 0.0


class DecisionState(BaseModel):
    """Estado estructurado que se entrega al motor de decisión (Laya)."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    source: Source
    correlation_id: str
    features: InferenceFeatures
    evidence: Evidence
    thresholds: dict[str, float]
    model_version: str | None = None
    feature_version: str | None = None


class LayaResult(BaseModel):
    """Resultado de la consulta a Laya (segunda opinión opcional)."""

    model_config = ConfigDict(extra="forbid")

    eligible: bool = False
    invoked: bool = False
    status: LayaStatus = LayaStatus.SKIPPED
    decision: Decision | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    mode: str | None = None
    latency_ms: float = Field(default=0.0, ge=0.0)
    error: str | None = None


class DecisionResult(BaseModel):
    """Decisión final con trazabilidad completa."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    source: Source
    correlation_id: str
    event_id: str | None = None
    primary_decision: Decision
    primary_score: float | None = Field(default=None, ge=0.0, le=1.0)
    laya: LayaResult = Field(default_factory=LayaResult)
    final_decision: Decision
    fallback_level: FallbackLevel
    fallback_reason: str
    explanation: list[str] = Field(default_factory=list)
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    model_version: str | None = None
    feature_version: str | None = None
    # Contexto de la operación (aditivo): permite que un solo evento
    # decision.created sea autosuficiente para la vista realtime.
    transaction: Transaction | None = None
    state: DecisionState | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

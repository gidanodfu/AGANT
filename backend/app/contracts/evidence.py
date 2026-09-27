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

"""Contratos de evidencia: reglas, ML y contexto de grafo."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import ComponentStatus, Decision
from .transaction import GraphContext


class RuleResult(BaseModel):
    """Resultado de una regla determinista."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    triggered: bool
    decision: Decision | None = None
    severity: str = "info"
    reason: str = ""


class MLResult(BaseModel):
    """Resultado del proveedor de ML."""

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    decision: Decision | None = None
    model_version: str | None = None
    feature_version: str | None = None
    latency_ms: float = Field(default=0.0, ge=0.0)


class GraphAvailability(BaseModel):
    """Disponibilidad y contexto del proveedor de grafo."""

    model_config = ConfigDict(extra="forbid")

    status: ComponentStatus = ComponentStatus.UNAVAILABLE
    context: GraphContext = Field(default_factory=GraphContext)


class Evidence(BaseModel):
    """Evidencia agregada de reglas + ML + grafo, antes de decidir."""

    model_config = ConfigDict(extra="forbid")

    rules: list[RuleResult] = Field(default_factory=list)
    ml: MLResult = Field(default_factory=MLResult)
    graph: GraphAvailability = Field(default_factory=GraphAvailability)
    components: dict[str, ComponentStatus] = Field(default_factory=dict)
    rule_score: float | None = None

    @property
    def rules_triggered(self) -> list[RuleResult]:
        return [rule for rule in self.rules if rule.triggered]

    def forced_decision(self) -> Decision | None:
        """Decisión forzada por reglas de severidad ``critical`` (si existe)."""
        for rule in self.rules_triggered:
            if rule.severity == "critical" and rule.decision is not None:
                return rule.decision
        return None

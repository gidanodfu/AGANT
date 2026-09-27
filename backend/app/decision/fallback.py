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

"""Política de fallback basada en disponibilidad real de componentes.

Nivel 0: grafo + ML · Nivel 1: ML solo · Nivel 2: solo reglas.
La disponibilidad de Laya no altera el nivel de fallback.
"""

from __future__ import annotations

from ..contracts.enums import ComponentStatus, Decision, FallbackLevel
from ..contracts.evidence import Evidence


class FallbackPolicy:
    def level(self, evidence: Evidence) -> tuple[FallbackLevel, str]:
        ml_ok = evidence.ml.available
        graph_ok = evidence.graph.status is ComponentStatus.READY
        if ml_ok and graph_ok:
            return FallbackLevel.GRAPH_ML, "grafo y ML disponibles"
        if ml_ok:
            return FallbackLevel.ML_ONLY, "contexto de grafo no disponible"
        return FallbackLevel.RULES_ONLY, "modelo de ML no disponible"

    def primary(self, evidence: Evidence, level: FallbackLevel) -> tuple[Decision, float | None]:
        forced = evidence.forced_decision()
        if forced is not None:
            return forced, evidence.ml.score if evidence.ml.available else None

        if level in (FallbackLevel.GRAPH_ML, FallbackLevel.ML_ONLY) and evidence.ml.decision is not None:
            return evidence.ml.decision, evidence.ml.score

        for rule in evidence.rules_triggered:
            if rule.decision is not None:
                return rule.decision, evidence.ml.score if evidence.ml.available else None
        return Decision.LEGITIMATE, evidence.ml.score if evidence.ml.available else None

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

"""Construcción de un pipeline de decisión aislado para flujos (replay/live).

Cada flujo usa su propio estado de grafo para no contaminar el estado live.
"""

from __future__ import annotations

from ..config import Settings
from ..decision import DecisionEngine, DecisionStateBuilder
from ..decision.laya_engine import LayaDecisionEngine
from ..evidence.engine import EvidenceEngine
from ..evidence.graph_provider import GraphContextProvider
from ..evidence.ml_provider import MLDecisionProvider
from ..service import DecisionService


def build_flow_service(
    settings: Settings, state, laya_engine: LayaDecisionEngine, decision_mode: str | None = None
) -> tuple[DecisionService, bool]:
    """Devuelve (service, laya_active) con grafo y ML propios del flujo."""
    graph = GraphContextProvider(settings)
    ml = MLDecisionProvider(settings)
    ml.load()
    evidence = EvidenceEngine(settings, graph_provider=graph, ml=ml)
    engine = DecisionEngine(
        settings,
        evidence_engine=evidence,
        laya_engine=laya_engine,
        state_builder=DecisionStateBuilder(settings),
        decision_mode=decision_mode,
    )
    service = DecisionService(state, engine=engine)
    laya_active = laya_engine.enabled and laya_engine.status.value == "ready"
    return service, laya_active

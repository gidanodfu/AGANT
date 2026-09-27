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

"""Tests de caracterización del proveedor de contexto de grafo."""

from __future__ import annotations

from app.config import Settings
from app.contracts import (
    ComponentStatus,
    Decision,
    Evidence,
    FallbackLevel,
    GraphAvailability,
    MLResult,
)
from app.contracts.transaction import Transaction
from app.decision import FallbackPolicy
from app.evidence.graph_provider import GraphContextProvider


def _tx(tx_id: str, step: int, origin: str = "C1", dest: str = "M1") -> Transaction:
    return Transaction(
        transaction_id=tx_id,
        step=step,
        type="TRANSFER",
        amount=10.0,
        name_orig=origin,
        old_balance_org=100.0,
        name_dest=dest,
        old_balance_dest=0.0,
    )


def test_provide_reports_ready(settings: Settings):
    provider = GraphContextProvider(settings)
    availability = provider.provide(_tx("T1", 1))
    assert availability.status is ComponentStatus.READY


def test_provide_context_is_causal(settings: Settings):
    provider = GraphContextProvider(settings)
    provider.provide(_tx("T1", 1, "C1", "M1"))
    same_step = provider.provide(_tx("T2", 1, "C1", "M2"))
    assert same_step.context.origin_degree_before == 0
    next_step = provider.provide(_tx("T3", 2, "C1", "M1"))
    assert next_step.context.origin_degree_before == 2
    assert next_step.context.destination_degree_before == 1


def test_graph_failure_is_reported_unavailable(settings: Settings, monkeypatch):
    provider = GraphContextProvider(settings)

    def boom(_step: int) -> None:
        raise RuntimeError("grafo caído")

    monkeypatch.setattr(provider.state, "advance", boom)
    availability = provider.provide(_tx("T1", 1))
    assert availability.status is ComponentStatus.UNAVAILABLE


def test_fallback_level_is_ml_only_when_graph_unavailable():
    evidence = Evidence(
        graph=GraphAvailability(status=ComponentStatus.UNAVAILABLE),
        ml=MLResult(available=True, score=0.9, decision=Decision.LEGITIMATE),
    )
    assert FallbackPolicy().level(evidence)[0] is FallbackLevel.ML_ONLY

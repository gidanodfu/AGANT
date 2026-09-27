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

"""Tests de la política de fallback."""

from __future__ import annotations

from app.contracts import (
    ComponentStatus,
    Decision,
    Evidence,
    FallbackLevel,
    GraphAvailability,
    MLResult,
    RuleResult,
)
from app.decision import FallbackPolicy

POLICY = FallbackPolicy()


def _evidence(ml_available: bool, graph_ok: bool, ml_decision: Decision | None = None) -> Evidence:
    return Evidence(
        ml=MLResult(available=ml_available, score=0.9 if ml_available else None, decision=ml_decision),
        graph=GraphAvailability(
            status=ComponentStatus.READY if graph_ok else ComponentStatus.UNAVAILABLE
        ),
    )


def test_levels_follow_availability():
    assert POLICY.level(_evidence(True, True))[0] is FallbackLevel.GRAPH_ML
    assert POLICY.level(_evidence(True, False))[0] is FallbackLevel.ML_ONLY
    assert POLICY.level(_evidence(False, True))[0] is FallbackLevel.RULES_ONLY
    assert POLICY.level(_evidence(False, False))[0] is FallbackLevel.RULES_ONLY


def test_primary_uses_ml_when_available():
    decision, score = POLICY.primary(_evidence(True, True, Decision.FRAUD), FallbackLevel.GRAPH_ML)
    assert decision is Decision.FRAUD and score == 0.9


def test_critical_rule_forces_decision_over_ml():
    evidence = _evidence(True, True, Decision.LEGITIMATE)
    evidence.rules.append(
        RuleResult(rule_id="R001", triggered=True, decision=Decision.FRAUD, severity="critical")
    )
    decision, _ = POLICY.primary(evidence, FallbackLevel.GRAPH_ML)
    assert decision is Decision.FRAUD


def test_rules_only_falls_back_to_legitimate():
    decision, score = POLICY.primary(_evidence(False, False), FallbackLevel.RULES_ONLY)
    assert decision is Decision.LEGITIMATE and score is None

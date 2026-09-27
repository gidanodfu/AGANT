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

"""Tests del motor de decisión y de la integración con Laya."""

from __future__ import annotations

from app.config import Settings
from app.contracts import (
    ComponentStatus,
    Decision,
    Evidence,
    FallbackLevel,
    GraphAvailability,
    GraphContext,
    LayaResult,
    LayaStatus,
    MLResult,
    Source,
    Transaction,
)
from app.decision import DecisionEngine
from app.decision.laya_engine import LayaDecisionEngine
from app.evidence.engine import EvidenceEngine


class StubML:
    def __init__(self, available: bool, decision: Decision | None, score: float | None = 0.9) -> None:
        self._available = available
        self._decision = decision
        self._score = score

    def predict(self, features) -> MLResult:
        return MLResult(
            available=self._available,
            score=self._score if self._available else None,
            decision=self._decision if self._available else None,
            model_version="stub",
            feature_version="online_v1",
        )


class StubGraph:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok

    def provide(self, transaction: Transaction) -> GraphAvailability:
        return GraphAvailability(
            status=ComponentStatus.READY if self.ok else ComponentStatus.UNAVAILABLE,
            context=GraphContext(),
        )


class StubLaya:
    def __init__(self, status: LayaStatus, decision: Decision | None = None) -> None:
        self.status = ComponentStatus.READY
        self._status = status
        self._decision = decision
        self.calls = 0

    def evaluate(self, state, primary: Decision, *, decide_all: bool = False) -> LayaResult:
        invoked = (decide_all or primary is Decision.SUSPICIOUS) and self._status in (
            LayaStatus.SUCCEEDED,
            LayaStatus.FAILED,
        )
        if invoked:
            self.calls += 1
        return LayaResult(
            eligible=primary is Decision.SUSPICIOUS,
            invoked=invoked,
            status=self._status,
            decision=self._decision if self._status is LayaStatus.SUCCEEDED else None,
            mode="pretrained",
        )


def _engine(ml: StubML, graph: StubGraph, laya: StubLaya, settings: Settings | None = None) -> DecisionEngine:
    settings = settings or Settings(laya_mode="disabled")
    evidence = EvidenceEngine(settings, graph_provider=graph, ml=ml)
    return DecisionEngine(settings, evidence_engine=evidence, laya_engine=laya)


def _transaction(**overrides) -> Transaction:
    base = dict(
        transaction_id="T1",
        step=10,
        type="TRANSFER",
        amount=100.0,
        name_orig="C1",
        old_balance_org=1000.0,
        name_dest="M1",
        old_balance_dest=0.0,
    )
    base.update(overrides)
    return Transaction(**base)


def test_legitimate_skips_laya():
    result = _engine(StubML(True, Decision.LEGITIMATE), StubGraph(), StubLaya(LayaStatus.SKIPPED)).decide(
        _transaction()
    )
    assert result.final_decision is Decision.LEGITIMATE
    assert result.laya.invoked is False
    assert result.fallback_level is FallbackLevel.GRAPH_ML


def test_flagged_fraud_forces_fraud_without_laya():
    laya = StubLaya(LayaStatus.SKIPPED)
    result = _engine(StubML(True, Decision.LEGITIMATE), StubGraph(), laya).decide(
        _transaction(is_flagged_fraud=True)
    )
    assert result.primary_decision is Decision.FRAUD
    assert result.final_decision is Decision.FRAUD
    assert laya.calls == 0


def test_suspicious_upgraded_by_laya_keeps_primary():
    result = _engine(StubML(True, Decision.SUSPICIOUS), StubGraph(), StubLaya(LayaStatus.SUCCEEDED, Decision.FRAUD)).decide(
        _transaction()
    )
    assert result.primary_decision is Decision.SUSPICIOUS
    assert result.final_decision is Decision.FRAUD
    assert result.laya.invoked is True


def test_suspicious_downgraded_by_laya():
    result = _engine(StubML(True, Decision.SUSPICIOUS), StubGraph(), StubLaya(LayaStatus.SUCCEEDED, Decision.LEGITIMATE)).decide(
        _transaction()
    )
    assert result.primary_decision is Decision.SUSPICIOUS
    assert result.final_decision is Decision.LEGITIMATE


def test_suspicious_kept_when_laya_returns_suspicious():
    result = _engine(StubML(True, Decision.SUSPICIOUS), StubGraph(), StubLaya(LayaStatus.SUCCEEDED, Decision.SUSPICIOUS)).decide(
        _transaction()
    )
    assert result.primary_decision is Decision.SUSPICIOUS
    assert result.final_decision is Decision.SUSPICIOUS
    assert result.laya.invoked is True


def test_laya_all_mode_decides_everything():
    engine = _engine(StubML(True, Decision.LEGITIMATE), StubGraph(), StubLaya(LayaStatus.SUCCEEDED, Decision.FRAUD))
    result = engine.decide(_transaction(), decision_mode="laya_all")
    assert result.primary_decision is Decision.LEGITIMATE
    assert result.final_decision is Decision.FRAUD
    assert result.laya.invoked is True


def test_laya_failure_keeps_primary():
    result = _engine(StubML(True, Decision.SUSPICIOUS), StubGraph(), StubLaya(LayaStatus.FAILED)).decide(
        _transaction()
    )
    assert result.laya.status is LayaStatus.FAILED
    assert result.final_decision is Decision.SUSPICIOUS


def test_ml_unavailable_uses_rules_only():
    result = _engine(StubML(False, None), StubGraph(), StubLaya(LayaStatus.DISABLED)).decide(_transaction())
    assert result.fallback_level is FallbackLevel.RULES_ONLY
    assert result.final_decision is Decision.LEGITIMATE


def test_graph_unavailable_uses_ml_only():
    result = _engine(StubML(True, Decision.LEGITIMATE), StubGraph(ok=False), StubLaya(LayaStatus.DISABLED)).decide(
        _transaction()
    )
    assert result.fallback_level is FallbackLevel.ML_ONLY


def test_laya_engine_disabled_and_unavailable_states():
    from app.contracts import DecisionState
    from app.contracts.transaction import InferenceFeatures

    disabled = LayaDecisionEngine(Settings(laya_enabled=False, laya_mode="disabled"))

    decision_state = DecisionState(
        transaction_id="T1",
        source=Source.LIVE,
        correlation_id="c",
        features=InferenceFeatures(step=1, amount=1, origin_old_balance=1, destination_old_balance=0),
        evidence=Evidence(),
        thresholds={"suspicious": 0.2, "fraud": 0.5},
    )
    assert disabled.evaluate(decision_state, Decision.SUSPICIOUS).status is LayaStatus.DISABLED

    pending = LayaDecisionEngine(Settings(laya_enabled=True, laya_mode="pretrained"))
    outcome = pending.evaluate(decision_state, Decision.SUSPICIOUS)
    assert outcome.status is LayaStatus.UNAVAILABLE and outcome.invoked is False
    skipped = pending.evaluate(decision_state, Decision.LEGITIMATE)
    assert skipped.status is LayaStatus.SKIPPED

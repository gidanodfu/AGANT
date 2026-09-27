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

"""Motor de decisión: evidencia → estado → Laya → fallback → decisión.

Pieza delgada de composición, sin lógica de negocio: cada etapa vive en
su componente. La decisión primaria nunca se pierde cuando Laya hace
upgrade/downgrade.
"""

from __future__ import annotations

import time

from ..config import Settings
from ..contracts.decision import DecisionResult, LatencyBreakdown
from ..contracts.enums import Decision, LayaStatus, Source
from ..contracts.transaction import Transaction
from ..evidence.engine import EvidenceEngine
from .fallback import FallbackPolicy
from .laya_engine import LayaDecisionEngine
from .state_builder import DecisionStateBuilder


class DecisionEngine:
    def __init__(
        self,
        settings: Settings,
        *,
        evidence_engine: EvidenceEngine | None = None,
        laya_engine: LayaDecisionEngine | None = None,
        policy: FallbackPolicy | None = None,
        state_builder: DecisionStateBuilder | None = None,
        decision_mode: str | None = None,
    ) -> None:
        self.settings = settings
        self.evidence_engine = evidence_engine or EvidenceEngine(settings)
        self.laya_engine = laya_engine or LayaDecisionEngine(settings)
        self.policy = policy or FallbackPolicy()
        self.state_builder = state_builder or DecisionStateBuilder(settings)
        self.decision_mode = decision_mode or settings.decision_mode

    def decide(
        self,
        transaction: Transaction,
        *,
        source: Source = Source.LIVE,
        correlation_id: str = "-",
        decision_mode: str | None = None,
    ) -> DecisionResult:
        total_start = time.perf_counter()

        features, evidence, timings = self.evidence_engine.evaluate(transaction)

        fallback_start = time.perf_counter()
        level, reason = self.policy.level(evidence)
        primary, primary_score = self.policy.primary(evidence, level)
        fallback_ms = (time.perf_counter() - fallback_start) * 1000.0

        state_start = time.perf_counter()
        state = self.state_builder.build(
            transaction_id=transaction.transaction_id,
            source=source,
            correlation_id=correlation_id,
            features=features,
            evidence=evidence,
        )
        state_ms = (time.perf_counter() - state_start) * 1000.0

        mode = decision_mode or self.decision_mode
        laya_result = self.laya_engine.evaluate(
            state, primary, decide_all=(mode == "laya_all")
        )
        final = self._apply_laya(primary, laya_result)

        latency = LatencyBreakdown(
            features_ms=timings.get("features_ms", 0.0),
            graph_ms=timings.get("graph_ms", 0.0),
            rules_ms=timings.get("rules_ms", 0.0),
            ml_ms=timings.get("ml_ms", 0.0),
            state_ms=state_ms,
            laya_ms=laya_result.latency_ms,
            fallback_ms=fallback_ms,
            total_ms=(time.perf_counter() - total_start) * 1000.0,
        )
        return DecisionResult(
            transaction_id=transaction.transaction_id,
            source=source,
            correlation_id=correlation_id,
            primary_decision=primary,
            primary_score=primary_score,
            laya=laya_result,
            final_decision=final,
            fallback_level=level,
            fallback_reason=reason,
            explanation=self._explain(evidence, laya_result, final),
            latency=latency,
            model_version=evidence.ml.model_version,
            feature_version=evidence.ml.feature_version,
            transaction=transaction,
            state=state,
        )

    def _apply_laya(self, primary: Decision, laya_result) -> Decision:
        if laya_result.status is LayaStatus.SUCCEEDED and laya_result.decision is not None:
            return laya_result.decision
        return primary

    def _explain(self, evidence, laya_result, final: Decision) -> list[str]:
        reasons = [rule.reason for rule in evidence.rules_triggered]
        if evidence.ml.available:
            reasons.append(f"score ML={evidence.ml.score:.4f}")
        else:
            reasons.append("modelo ML no disponible")
        if laya_result.invoked:
            reasons.append(
                f"Laya {laya_result.status.value}→{final.value} ({laya_result.latency_ms:.1f} ms)"
            )
        return reasons

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

"""Motor de decisión por lotes (alto rendimiento).

Mantiene la semántica online (features causales, reglas, grafo, Laya y
fallback por ítem) pero vectoriza la inferencia ML en lotes de
``batch_size``. No usa datos post-transacción.
"""

from __future__ import annotations

import time

from ..config import Settings
from ..contracts.decision import DecisionResult, LatencyBreakdown
from ..contracts.enums import ComponentStatus, Decision, LayaStatus, Source
from ..contracts.evidence import Evidence
from ..contracts.transaction import Transaction
from ..evidence.graph_provider import GraphContextProvider
from ..evidence.ml_provider import MLDecisionProvider
from ..evidence.rules_engine import RulesEngine
from ..features.feature_builder import FeatureBuilder
from .fallback import FallbackPolicy
from .laya_engine import LayaDecisionEngine
from .state_builder import DecisionStateBuilder


class BatchDecisionEngine:
    def __init__(
        self,
        settings: Settings,
        state,
        laya_engine: LayaDecisionEngine,
        *,
        batch_size: int = 32,
        decision_mode: str | None = None,
    ) -> None:
        self.settings = settings
        self.state = state
        self.batch_size = max(1, int(batch_size))
        self.decision_mode = decision_mode or settings.decision_mode
        self.decide_all = self.decision_mode == "laya_all"
        self.laya_batch = max(1, int(batch_size))
        self.laya = laya_engine
        self.graph = GraphContextProvider(settings)
        self.ml = MLDecisionProvider(settings)
        self.ml.load()
        self.rules = RulesEngine(settings)
        self.features = FeatureBuilder()
        self.policy = FallbackPolicy()
        self.state_builder = DecisionStateBuilder(settings)
        self.laya_active = laya_engine.enabled and laya_engine.status.value == "ready"

    def decide_block(
        self, transactions: list[Transaction], source: Source, correlation_id: str = "flow"
    ) -> list[DecisionResult]:
        prepared = []
        for transaction in transactions:
            start = time.perf_counter()
            graph = self.graph.provide(transaction)
            graph_ms = (time.perf_counter() - start) * 1000.0
            start = time.perf_counter()
            features = self.features.build(transaction, graph.context)
            features_ms = (time.perf_counter() - start) * 1000.0
            start = time.perf_counter()
            rule_results = self.rules.evaluate(transaction, graph.context)
            rules_ms = (time.perf_counter() - start) * 1000.0
            prepared.append((transaction, graph, features, rule_results, graph_ms, features_ms, rules_ms))

        ml_results: list = []
        for index in range(0, len(prepared), self.batch_size):
            chunk = prepared[index:index + self.batch_size]
            ml_results.extend(self.ml.predict_batch([item[2] for item in chunk]))

        # 1) evidencia + decisión primaria + estado (sin Laya todavía)
        built = []
        primaries = []
        states = []
        for index, (transaction, graph, features, rule_results, graph_ms, features_ms, rules_ms) in enumerate(prepared):
            ml_result = ml_results[index]
            evidence = Evidence(
                rules=rule_results,
                ml=ml_result,
                graph=graph,
                rule_score=self.rules.rule_score(rule_results),
                components={
                    "graph": graph.status,
                    "ml": ComponentStatus.READY if ml_result.available else ComponentStatus.UNAVAILABLE,
                    "rules": ComponentStatus.READY,
                },
            )
            start = time.perf_counter()
            level, reason = self.policy.level(evidence)
            primary, primary_score = self.policy.primary(evidence, level)
            fallback_ms = (time.perf_counter() - start) * 1000.0
            state = self.state_builder.build(
                transaction_id=transaction.transaction_id,
                source=source,
                correlation_id=correlation_id,
                features=features,
                evidence=evidence,
            )
            primaries.append(primary)
            states.append(state)
            built.append(
                (transaction, graph, features, rule_results, graph_ms, features_ms, rules_ms,
                 ml_result, evidence, level, reason, primary, primary_score, fallback_ms, state)
            )

        # 2) Laya en lote (micro-batching) — decide_all según el modo
        laya_results = self.laya.evaluate_batch(
            states, primaries, decide_all=self.decide_all, batch_size=self.laya_batch
        )

        # 3) ensamblado
        results: list[DecisionResult] = []
        for entry, laya_result in zip(built, laya_results):
            (transaction, graph, features, rule_results, graph_ms, features_ms, rules_ms,
             ml_result, evidence, level, reason, primary, primary_score, fallback_ms, state) = entry
            final = (
                laya_result.decision
                if laya_result.status is LayaStatus.SUCCEEDED and laya_result.decision is not None
                else primary
            )
            total = graph_ms + features_ms + rules_ms + ml_result.latency_ms + fallback_ms + laya_result.latency_ms
            results.append(
                DecisionResult(
                    transaction_id=transaction.transaction_id,
                    source=source,
                    correlation_id=correlation_id,
                    primary_decision=primary,
                    primary_score=primary_score,
                    laya=laya_result,
                    final_decision=final,
                    fallback_level=level,
                    fallback_reason=reason,
                    explanation=[rule.reason for rule in rule_results if rule.triggered],
                    latency=LatencyBreakdown(
                        features_ms=features_ms,
                        graph_ms=graph_ms,
                        rules_ms=rules_ms,
                        ml_ms=ml_result.latency_ms,
                        fallback_ms=fallback_ms,
                        laya_ms=laya_result.latency_ms,
                        total_ms=total,
                    ),
                    model_version=ml_result.model_version,
                    feature_version=ml_result.feature_version,
                    transaction=transaction,
                    state=state,
                )
            )
        return results

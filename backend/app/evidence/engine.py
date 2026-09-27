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

"""EvidenceEngine: agrega reglas + ML + grafo en evidencia."""

from __future__ import annotations

import time

from ..config import Settings
from ..contracts.enums import ComponentStatus
from ..contracts.evidence import Evidence
from ..contracts.transaction import InferenceFeatures, Transaction
from ..features.feature_builder import FeatureBuilder
from .graph_provider import GraphContextProvider
from .ml_provider import MLDecisionProvider
from .rules_engine import RulesEngine


class EvidenceEngine:
    def __init__(
        self,
        settings: Settings,
        *,
        graph_provider: GraphContextProvider | None = None,
        rules: RulesEngine | None = None,
        ml: MLDecisionProvider | None = None,
        feature_builder: FeatureBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.graph_provider = graph_provider or GraphContextProvider(settings)
        self.rules = rules or RulesEngine(settings)
        self.ml = ml or MLDecisionProvider(settings)
        self.feature_builder = feature_builder or FeatureBuilder()

    def evaluate(
        self, transaction: Transaction
    ) -> tuple[InferenceFeatures, Evidence, dict[str, float]]:
        timings: dict[str, float] = {}

        start = time.perf_counter()
        graph = self.graph_provider.provide(transaction)
        timings["graph_ms"] = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        features = self.feature_builder.build(transaction, graph.context)
        timings["features_ms"] = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        rule_results = self.rules.evaluate(transaction, graph.context)
        timings["rules_ms"] = (time.perf_counter() - start) * 1000.0

        start = time.perf_counter()
        ml_result = self.ml.predict(features)
        timings["ml_ms"] = (time.perf_counter() - start) * 1000.0

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
        return features, evidence, timings

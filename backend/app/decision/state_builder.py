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

"""Construcción del estado estructurado que consume el motor de decisión."""

from __future__ import annotations

from ..config import Settings
from ..contracts.decision import DecisionState
from ..contracts.enums import Source
from ..contracts.evidence import Evidence
from ..contracts.transaction import InferenceFeatures


class DecisionStateBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(
        self,
        *,
        transaction_id: str,
        source: Source,
        correlation_id: str,
        features: InferenceFeatures,
        evidence: Evidence,
    ) -> DecisionState:
        return DecisionState(
            transaction_id=transaction_id,
            source=source,
            correlation_id=correlation_id,
            features=features,
            evidence=evidence,
            thresholds={
                "suspicious": self.settings.threshold_suspicious,
                "fraud": self.settings.threshold_fraud,
            },
            model_version=evidence.ml.model_version,
            feature_version=evidence.ml.feature_version,
        )

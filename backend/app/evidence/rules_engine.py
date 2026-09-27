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

"""Motor de reglas deterministas: evidencia explícita y fallback.

Sólo ``R001`` (indicador del protocolo de inferencia) fuerza ``FRAUD``.
El resto aporta explicabilidad. ``isFraud`` (ground truth) nunca se usa.
"""

from __future__ import annotations

from ..config import Settings
from ..contracts.enums import Decision
from ..contracts.evidence import RuleResult
from ..contracts.transaction import GraphContext, Transaction, TransactionType


class RulesEngine:
    def __init__(self, settings: Settings) -> None:
        self.high_amount = settings.rule_high_amount
        self.dest_fan_in = settings.rule_dest_fan_in

    def evaluate(self, transaction: Transaction, graph: GraphContext) -> list[RuleResult]:
        results: list[RuleResult] = []

        results.append(
            RuleResult(
                rule_id="R001",
                triggered=transaction.is_flagged_fraud,
                decision=Decision.FRAUD if transaction.is_flagged_fraud else None,
                severity="critical",
                reason="Transacción marcada por el protocolo de inferencia (isFlaggedFraud).",
            )
        )

        high_value = (
            transaction.type in (TransactionType.TRANSFER, TransactionType.CASH_OUT)
            and transaction.amount >= self.high_amount
        )
        results.append(
            RuleResult(
                rule_id="R002",
                triggered=high_value,
                decision=Decision.SUSPICIOUS if high_value else None,
                severity="warning",
                reason="Operación de alto riesgo con importe elevado.",
            )
        )

        drained = transaction.old_balance_org > 0 and transaction.amount >= transaction.old_balance_org
        results.append(
            RuleResult(
                rule_id="R003",
                triggered=drained,
                decision=Decision.SUSPICIOUS if drained else None,
                severity="warning",
                reason="La cuenta origen quedaría vaciada con esta operación.",
            )
        )

        fan_in = graph.destination_unique_origins_before >= self.dest_fan_in
        results.append(
            RuleResult(
                rule_id="R004",
                triggered=fan_in,
                decision=None,
                severity="info",
                reason="El destino concentra transacciones desde muchas cuentas distintas.",
            )
        )
        return results

    def rule_score(self, results: list[RuleResult]) -> float:
        weights = {"critical": 1.0, "warning": 0.25, "info": 0.05}
        total = sum(weights.get(rule.severity, 0.0) for rule in results if rule.triggered)
        return min(1.0, total)

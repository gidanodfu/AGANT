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

"""Construcción de las 15 features online a partir de la transacción y el grafo."""

from __future__ import annotations

from ..contracts.transaction import GraphContext, InferenceFeatures, Transaction, TransactionType

_ONE_HOT = {
    TransactionType.CASH_IN: "type_CASH_IN",
    TransactionType.CASH_OUT: "type_CASH_OUT",
    TransactionType.DEBIT: "type_DEBIT",
    TransactionType.PAYMENT: "type_PAYMENT",
    TransactionType.TRANSFER: "type_TRANSFER",
}


class FeatureBuilder:
    """Combina 9 features tabulares con 6 de grafo, sin datos post-transacción."""

    def build(self, transaction: Transaction, graph: GraphContext) -> InferenceFeatures:
        one_hot = {name: 0.0 for name in _ONE_HOT.values()}
        one_hot[_ONE_HOT[transaction.type]] = 1.0
        return InferenceFeatures(
            step=float(transaction.step),
            amount=float(transaction.amount),
            origin_old_balance=float(transaction.old_balance_org),
            destination_old_balance=float(transaction.old_balance_dest),
            origin_degree_before=float(graph.origin_degree_before),
            destination_degree_before=float(graph.destination_degree_before),
            origin_unique_destinations_before=float(graph.origin_unique_destinations_before),
            destination_unique_origins_before=float(graph.destination_unique_origins_before),
            edge_count_before=float(graph.edge_count_before),
            edge_seen_before=float(graph.edge_seen_before),
            **one_hot,
        )

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

"""Tests de caracterización del proveedor de contexto de grafo."""

from __future__ import annotations

from app.config import Settings
from app.contracts import ComponentStatus
from app.contracts.transaction import Transaction
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

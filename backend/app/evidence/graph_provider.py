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

"""Proveedor de contexto de grafo (FeatureBuilder causal acotado)."""

from __future__ import annotations

from ..config import Settings
from ..contracts.enums import ComponentStatus
from ..contracts.evidence import GraphAvailability
from ..contracts.transaction import Transaction
from ..features.graph_state import GraphState


class GraphContextProvider:
    def __init__(self, settings: Settings) -> None:
        self.state = GraphState(settings.graph_max_accounts, settings.graph_max_edges)
        self._status = ComponentStatus.READY

    def provide(self, transaction: Transaction) -> GraphAvailability:
        self.state.advance(transaction.step)
        context = self.state.context(transaction.name_orig, transaction.name_dest)
        self.state.observe(transaction.name_orig, transaction.name_dest, transaction.step)
        return GraphAvailability(status=self._status, context=context)

    def reset(self) -> None:
        self.state.reset()

    def commit(self) -> None:
        self.state.flush()

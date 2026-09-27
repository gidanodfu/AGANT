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

"""Estado de grafo incremental y causal para la ruta online.

Emula ``RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING`` sobre
``step``: el contexto de una transacción sólo ve pasos estrictamente
anteriores. Las actualizaciones del ``step`` en curso se difieren hasta
que avanza el paso, de modo que dos transacciones del mismo instante no
se ven entre sí. El estado está acotado por LRU.
"""

from __future__ import annotations

from collections import OrderedDict

from ..contracts.transaction import GraphContext


class GraphState:
    def __init__(self, max_accounts: int, max_edges: int) -> None:
        self.max_accounts = max_accounts
        self.max_edges = max_edges
        self._origin_degree: OrderedDict[str, int] = OrderedDict()
        self._destination_degree: OrderedDict[str, int] = OrderedDict()
        self._origin_destinations: OrderedDict[str, set[str]] = OrderedDict()
        self._destination_origins: OrderedDict[str, set[str]] = OrderedDict()
        self._edges: OrderedDict[tuple[str, str], int] = OrderedDict()
        self._pending: list[tuple[str, str]] = []
        self._step: int | None = None
        self._updates = 0

    @property
    def accounts(self) -> int:
        return len(self._origin_degree) + len(self._destination_degree)

    @property
    def edges(self) -> int:
        return len(self._edges)

    def advance(self, step: int) -> None:
        """Confirma los pasos anteriores cuando aparece un ``step`` nuevo."""
        if self._step is None:
            self._step = step
        elif step != self._step:
            self._flush()
            self._step = step

    def context(self, origin: str, destination: str, step: int | None = None) -> GraphContext:
        if step is not None:
            self.advance(step)
        return GraphContext(
            origin_degree_before=self._origin_degree.get(origin, 0),
            destination_degree_before=self._destination_degree.get(destination, 0),
            origin_unique_destinations_before=len(self._origin_destinations.get(origin, ())),
            destination_unique_origins_before=len(self._destination_origins.get(destination, ())),
            edge_count_before=self._edges.get((origin, destination), 0),
            edge_seen_before=1 if self._edges.get((origin, destination), 0) > 0 else 0,
        )

    def observe(self, origin: str, destination: str, step: int) -> None:
        """Registra la transacción para pasos futuros; no altera el contexto actual."""
        self.advance(step)
        self._pending.append((origin, destination))

    def flush(self) -> None:
        self._flush()
        self._pending.clear()

    def reset(self) -> None:
        self.__init__(self.max_accounts, self.max_edges)

    def _flush(self) -> None:
        for origin, destination in self._pending:
            self._apply(origin, destination)
        self._pending.clear()

    def _apply(self, origin: str, destination: str) -> None:
        self._origin_degree[origin] = self._origin_degree.get(origin, 0) + 1
        self._destination_degree[destination] = self._destination_degree.get(destination, 0) + 1
        self._origin_destinations.setdefault(origin, set()).add(destination)
        self._destination_origins.setdefault(destination, set()).add(origin)
        pair = (origin, destination)
        self._edges[pair] = self._edges.get(pair, 0) + 1
        self._touch(origin, destination)
        self._updates += 1
        if self._updates % 4096 == 0:
            self._evict()

    def _touch(self, origin: str, destination: str) -> None:
        for store, key in (
            (self._origin_degree, origin),
            (self._destination_degree, destination),
            (self._origin_destinations, origin),
            (self._destination_origins, destination),
            (self._edges, (origin, destination)),
        ):
            if key in store:
                store.move_to_end(key)

    def _evict(self) -> None:
        while len(self._edges) > self.max_edges:
            pair, _ = self._edges.popitem(last=False)
            remaining = self._edges.get(pair, 0)
            if remaining == 0:
                self._origin_destinations.get(pair[0], set()).discard(pair[1])
                self._destination_origins.get(pair[1], set()).discard(pair[0])
        while self.accounts > self.max_accounts:
            origin, _ = self._origin_degree.popitem(last=False)
            self._origin_destinations.pop(origin, None)
            destination, _ = self._destination_degree.popitem(last=False)
            self._destination_origins.pop(destination, None)

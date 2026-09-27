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

"""Estado de la aplicación y buffer reciente para bootstrap del frontend."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ..config import Settings
from ..contracts.decision import DecisionResult
from ..contracts.enums import Source
from ..decision.engine import DecisionEngine
from ..errors import ErrorManager
from ..events import EventBus
from ..observability.metrics import MetricsCollector


@dataclass
class Store:
    """Ventana reciente. Guarda **referencias** (sin serializar por fila) y
    serializa únicamente al leer, de modo que cada transacción procesada queda
    en el historial sin coste de `model_dump` en la ruta caliente."""

    maxlen: int = 500
    transactions: deque = field(default_factory=deque)
    decisions: deque = field(default_factory=deque)
    laya_decisions: deque = field(default_factory=deque)

    def __post_init__(self) -> None:
        self.transactions = deque(maxlen=self.maxlen)
        self.decisions = deque(maxlen=self.maxlen)
        self.laya_decisions = deque(maxlen=self.maxlen)

    def add_transaction(self, transaction, source: Source, event_id: str) -> None:
        self.transactions.append(
            {"event_id": event_id, "source": source.value, "transaction": transaction}
        )

    def add_decision(self, result: DecisionResult, event_id: str) -> None:
        entry = {"event_id": event_id, "source": result.source.value, "result": result}
        self.decisions.append(entry)
        if result.laya.invoked:
            self.laya_decisions.append(entry)

    @staticmethod
    def _transaction_dict(entry: dict) -> dict:
        return {
            "event_id": entry["event_id"],
            "source": entry["source"],
            **entry["transaction"].model_dump(mode="json"),
        }

    @staticmethod
    def _decision_dict(entry: dict) -> dict:
        payload = entry["result"].model_dump(mode="json")
        payload["event_id"] = entry["event_id"]
        return payload

    def recent_transactions(self, limit: int, source: Source | None = None) -> list[dict]:
        items = [e for e in self.transactions if source is None or e["source"] == source.value]
        return [self._transaction_dict(entry) for entry in items[-limit:]]

    def recent_decisions(self, limit: int, source: Source | None = None) -> list[dict]:
        items = [e for e in self.decisions if source is None or e["source"] == source.value]
        return [self._decision_dict(entry) for entry in items[-limit:]]

    def recent_laya_decisions(self, limit: int) -> list[dict]:
        return [self._decision_dict(entry) for entry in list(self.laya_decisions)[-limit:]]

    def find_decision(self, transaction_id: str, source: str | None = None) -> dict | None:
        for entry in reversed(self.decisions):
            result = entry["result"]
            if result.transaction_id != transaction_id:
                continue
            if source is not None and entry["source"] != source:
                continue
            return self._decision_dict(entry)
        return None

    def neighborhood(self, account: str, limit: int = 60) -> list[dict]:
        items = [
            entry
            for entry in self.transactions
            if entry["transaction"].name_orig == account
            or entry["transaction"].name_dest == account
        ]
        return [self._transaction_dict(entry) for entry in items[-limit:]]


@dataclass
class AppState:
    settings: Settings
    errors: ErrorManager
    bus: EventBus
    metrics: MetricsCollector
    store: Store
    decision_engine: DecisionEngine
    startup_report: object | None = None
    ws_clients: int = 0
    replay: object | None = None
    ml: object | None = None
    laya: object | None = None
    live_drift: object | None = None

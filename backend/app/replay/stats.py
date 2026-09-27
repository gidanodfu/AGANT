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

"""Contadores y latencias de un flujo (replay o live), independientes del bucket de métricas."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.decision import DecisionResult
from ..contracts.enums import Decision, LayaStatus

_MAX_SAMPLES = 50_000


@dataclass
class FlowStats:
    processed: int = 0
    fraud: int = 0
    suspicious: int = 0
    legitimate: int = 0
    errors: int = 0
    laya_invocations: int = 0
    latencies: list[float] = field(default_factory=list)

    def note(self, result: DecisionResult) -> None:
        self.processed += 1
        if result.final_decision is Decision.FRAUD:
            self.fraud += 1
        elif result.final_decision is Decision.SUSPICIOUS:
            self.suspicious += 1
        else:
            self.legitimate += 1
        if result.laya.invoked:
            self.laya_invocations += 1
            if result.laya.status is LayaStatus.FAILED:
                self.errors += 1
        self.latencies.append(float(result.latency.total_ms))
        if len(self.latencies) > _MAX_SAMPLES:
            del self.latencies[: _MAX_SAMPLES // 2]

    def p95(self) -> float:
        if not self.latencies:
            return 0.0
        ordered = sorted(self.latencies)
        return ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))]

    def snapshot(self) -> dict:
        return {
            "processed": self.processed,
            "fraud": self.fraud,
            "suspicious": self.suspicious,
            "legitimate": self.legitimate,
            "errors": self.errors,
            "laya_invocations": self.laya_invocations,
            "latency_p95_ms": self.p95(),
        }

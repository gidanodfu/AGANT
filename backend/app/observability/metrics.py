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

"""Métricas en memoria, separadas estrictamente por ``source`` (live/replay)."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field

from ..contracts.decision import DecisionResult
from ..contracts.enums import Decision, LayaStatus, Source
from ..contracts.metrics import MetricSnapshot, Percentiles

_STAGES = ("features_ms", "graph_ms", "rules_ms", "ml_ms", "state_ms", "laya_ms", "total_ms")
_MAX_SAMPLES = 20_000
_STATS_TTL_S = 2.0


def _percentiles(values: list[float]) -> Percentiles:
    if not values:
        return Percentiles()
    ordered = sorted(values)
    n = len(ordered)

    def at(q: float) -> float:
        return ordered[min(n - 1, int(q * (n - 1)))]

    return Percentiles(p50=at(0.50), p95=at(0.95), p99=at(0.99), count=n)


@dataclass
class _Bucket:
    processed: int = 0
    fraud: int = 0
    suspicious: int = 0
    legitimate: int = 0
    laya_invocations: int = 0
    laya_failures: int = 0
    started_at: float = field(default_factory=time.perf_counter)
    stages: dict[str, list[float]] = field(default_factory=lambda: {s: [] for s in _STAGES})


class MetricsCollector:
    def __init__(self) -> None:
        self._buckets = {Source.LIVE.value: _Bucket(), Source.REPLAY.value: _Bucket()}
        self.error_counts: Counter[str] = Counter()
        self._stats_cache: dict[str, tuple[float, dict]] = {}

    def _stats(self, source: Source) -> dict[str, Percentiles]:
        """Percentiles cacheados (TTL) para no re-ordenar en cada tick SSE."""
        cached = self._stats_cache.get(source.value)
        now = time.perf_counter()
        if cached is not None and now - cached[0] < _STATS_TTL_S:
            return cached[1]
        bucket = self._buckets[source.value]
        stats = {stage: _percentiles(bucket.stages[stage]) for stage in _STAGES}
        self._stats_cache[source.value] = (now, stats)
        return stats

    def record_decision(self, result: DecisionResult) -> None:
        bucket = self._buckets[result.source.value]
        bucket.processed += 1
        if result.final_decision is Decision.FRAUD:
            bucket.fraud += 1
        elif result.final_decision is Decision.SUSPICIOUS:
            bucket.suspicious += 1
        else:
            bucket.legitimate += 1
        if result.laya.invoked:
            bucket.laya_invocations += 1
            if result.laya.status is LayaStatus.FAILED:
                bucket.laya_failures += 1
        latency = result.latency
        for stage in _STAGES:
            if stage == "laya_ms" and not result.laya.invoked:
                # No contaminar la latencia de Laya con ceros.
                continue
            bucket.stages[stage].append(float(getattr(latency, stage)))
            if len(bucket.stages[stage]) > _MAX_SAMPLES:
                del bucket.stages[stage][:_MAX_SAMPLES // 2]

    def record_error(self, severity: str, source: str = Source.LIVE.value) -> None:
        self.error_counts[f"{source}:{severity}"] += 1

    def reset_source(self, source: Source) -> None:
        self._buckets[source.value] = _Bucket()

    def stage_stats(self, source: Source) -> dict[str, dict]:
        return {stage: value.model_dump() for stage, value in self._stats(source).items()}

    def snapshot(self, source: Source, *, bus_stats: dict | None = None, ws_clients: int = 0) -> MetricSnapshot:
        bucket = self._buckets[source.value]
        elapsed = max(1e-6, time.perf_counter() - bucket.started_at)
        errors = sum(v for k, v in self.error_counts.items() if k.startswith(source.value))
        return MetricSnapshot(
            source=source.value,
            processed=bucket.processed,
            fraud=bucket.fraud,
            suspicious=bucket.suspicious,
            legitimate=bucket.legitimate,
            throughput_tps=bucket.processed / elapsed,
            latency=self._stats(source)["total_ms"],
            laya_invocations=bucket.laya_invocations,
            laya_failures=bucket.laya_failures,
            error_rate=errors / max(1, bucket.processed),
            ws_clients=ws_clients,
            queue_depth=(bus_stats or {}).get("queue_depth", 0),
            events_published=(bus_stats or {}).get("events_published", 0),
            events_dropped=(bus_stats or {}).get("events_dropped", 0),
        )

    def all_snapshots(self, *, bus_stats: dict | None = None, ws_clients: int = 0) -> dict[str, dict]:
        return {
            source.value: self.snapshot(source, bus_stats=bus_stats, ws_clients=ws_clients).model_dump(mode="json")
            for source in (Source.LIVE, Source.REPLAY)
        }

    def snapshot_payload(self, *, bus_stats: dict | None = None, ws_clients: int = 0) -> dict:
        """Forma única compartida por HTTP y SSE (evita divergencias de contrato)."""
        return {
            "snapshots": self.all_snapshots(bus_stats=bus_stats, ws_clients=ws_clients),
            "stages": {
                "live": self.stage_stats(Source.LIVE),
                "replay": self.stage_stats(Source.REPLAY),
            },
            "event_bus": bus_stats or {},
        }

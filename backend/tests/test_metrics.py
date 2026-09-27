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

"""Tests de métricas separadas live/replay."""

from __future__ import annotations

from app.contracts import (
    Decision,
    DecisionResult,
    FallbackLevel,
    LatencyBreakdown,
    LayaResult,
    LayaStatus,
    Source,
)
from app.observability import MetricsCollector


def _result(source: Source, final: Decision, *, invoked: bool = False, total: float = 5.0) -> DecisionResult:
    return DecisionResult(
        transaction_id="T1",
        source=source,
        correlation_id="c",
        primary_decision=final,
        primary_score=0.5,
        laya=LayaResult(
            invoked=invoked,
            status=LayaStatus.SUCCEEDED if invoked else LayaStatus.SKIPPED,
            decision=Decision.FRAUD if invoked else None,
        ),
        final_decision=final,
        fallback_level=FallbackLevel.GRAPH_ML,
        fallback_reason="r",
        latency=LatencyBreakdown(total_ms=total),
    )


def test_live_and_replay_are_separated():
    metrics = MetricsCollector()
    metrics.record_decision(_result(Source.LIVE, Decision.LEGITIMATE, total=10.0))
    metrics.record_decision(_result(Source.LIVE, Decision.FRAUD, invoked=True, total=20.0))
    metrics.record_decision(_result(Source.REPLAY, Decision.SUSPICIOUS, total=30.0))

    live = metrics.snapshot(Source.LIVE)
    replay = metrics.snapshot(Source.REPLAY)
    assert live.processed == 2
    assert live.fraud == 1
    assert live.laya_invocations == 1
    assert replay.processed == 1
    assert replay.suspicious == 1
    assert live.latency.p50 == 10.0


def test_stage_stats_are_tracked():
    metrics = MetricsCollector()
    metrics.record_decision(_result(Source.LIVE, Decision.LEGITIMATE, total=12.0))
    stages = metrics.stage_stats(Source.LIVE)
    assert stages["total_ms"]["p95"] == 12.0
    assert "laya_ms" in stages


def test_error_rate_only_counts_source():
    metrics = MetricsCollector()
    metrics.record_decision(_result(Source.LIVE, Decision.LEGITIMATE))
    metrics.record_error("critical", source="replay")
    assert metrics.snapshot(Source.LIVE).error_rate == 0.0


def test_laya_latency_only_counts_invocations():
    metrics = MetricsCollector()
    metrics.record_decision(_result(Source.LIVE, Decision.LEGITIMATE, invoked=False, total=5.0))
    metrics.record_decision(_result(Source.LIVE, Decision.SUSPICIOUS, invoked=True, total=8.0))
    stats = metrics.stage_stats(Source.LIVE)
    assert stats["laya_ms"]["count"] == 1
    assert stats["total_ms"]["count"] == 2


def test_snapshot_payload_shape_is_single_source_of_truth():
    metrics = MetricsCollector()
    metrics.record_decision(_result(Source.LIVE, Decision.LEGITIMATE))
    metrics.record_decision(_result(Source.REPLAY, Decision.FRAUD))
    payload = metrics.snapshot_payload(bus_stats={"queue_depth": 0}, ws_clients=2)
    assert set(payload) == {"snapshots", "stages", "event_bus"}
    assert payload["snapshots"]["live"]["processed"] == 1
    assert payload["snapshots"]["replay"]["fraud"] == 1
    assert "total_ms" in payload["stages"]["live"]
    assert payload["snapshots"]["live"]["ws_clients"] == 2

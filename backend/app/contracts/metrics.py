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

"""Contratos de métricas agregadas y de modelo."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class Percentiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    count: int = 0


class MetricSnapshot(BaseModel):
    """Instantánea de métricas separadas por ``source`` (live/replay)."""

    model_config = ConfigDict(extra="forbid")

    source: str
    processed: int = 0
    fraud: int = 0
    suspicious: int = 0
    legitimate: int = 0
    throughput_tps: float = 0.0
    latency: Percentiles = Field(default_factory=Percentiles)
    laya_invocations: int = 0
    laya_failures: int = 0
    error_rate: float = 0.0
    ws_clients: int = 0
    queue_depth: int = 0
    events_published: int = 0
    events_dropped: int = 0
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelMetrics(BaseModel):
    """Métricas de evaluación de modelo, con procedencia completa."""

    model_config = ConfigDict(extra="forbid")

    dataset: str
    split: str
    threshold: float
    feature_version: str
    model_version: str
    precision: float
    recall: float
    f1: float
    roc_auc: float | None = None
    pr_auc: float | None = None
    tn: int = 0
    fp: int = 0
    fn: int = 0
    tp: int = 0
    rows: int = 0
    fraud: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

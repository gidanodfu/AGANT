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

"""Ejecuta un replay de PaySim sin servidor.

Uso:  .venv/bin/python scripts/replay.py [--with-laya] [--max-records N]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.api.state import Store  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.contracts.enums import Source  # noqa: E402
from app.decision import LayaDecisionEngine  # noqa: E402
from app.events import EventBus  # noqa: E402
from app.observability import MetricsCollector  # noqa: E402
from app.replay import ReplayEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay de PaySim (source=replay)")
    parser.add_argument("--with-laya", action="store_true")
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1, choices=[1, 32, 64])
    parser.add_argument("--block-size", type=int, default=None)
    parser.add_argument("--publish-mode", choices=["sampled", "all"], default=None)
    args = parser.parse_args()

    settings = get_settings()
    state = SimpleNamespace(
        settings=settings,
        bus=EventBus(subscriber_queue=settings.max_events),
        metrics=MetricsCollector(),
        store=Store(),
        laya=LayaDecisionEngine(settings),
    )
    if args.with_laya:
        state.laya.load()

    engine = ReplayEngine(
        state,
        with_laya=args.with_laya,
        max_records=args.max_records,
        batch_size=args.batch_size,
        block_size=args.block_size,
        publish_mode=args.publish_mode,
        publish=False,
    )
    start = time.perf_counter()
    asyncio.run(engine.run())
    elapsed = time.perf_counter() - start

    replay = state.metrics.snapshot(Source.REPLAY)
    live = state.metrics.snapshot(Source.LIVE)
    print(
        f"[replay] procesadas={engine.processed}/{engine.total} "
        f"elapsed={elapsed:.1f}s tps={engine.processed / elapsed:.1f} "
        f"fraude={replay.fraud} sospechosas={replay.suspicious} legit={replay.legitimate}"
    )
    print(
        f"[replay] p50={replay.latency.p50:.2f}ms p95={replay.latency.p95:.2f}ms "
        f"p99={replay.latency.p99:.2f}ms laya_invoc={replay.laya_invocations}"
    )
    print(f"[live] procesadas={live.processed} (no debe contaminarse)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

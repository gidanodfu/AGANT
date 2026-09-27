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

"""Benchmark E2E por etapas (p50/p95/p99) sobre PaySim.

Uso:  .venv/bin/python scripts/benchmark_e2e.py [--records N] [--batch B]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import numpy as np  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.contracts.enums import Source  # noqa: E402
from app.contracts.transaction import Transaction  # noqa: E402
from app.data.paysim_db import connect  # noqa: E402
from app.decision import DecisionEngine, DecisionStateBuilder, LayaDecisionEngine  # noqa: E402
from app.evidence.engine import EvidenceEngine  # noqa: E402
from app.evidence.graph_provider import GraphContextProvider  # noqa: E402
from app.evidence.ml_provider import MLDecisionProvider  # noqa: E402
from app.evidence.rules_engine import RulesEngine  # noqa: E402

_QUERY = (
    "SELECT step, type, amount, nameOrig, oldbalanceOrg, nameDest, oldbalanceDest, "
    "isFlaggedFraud FROM transactions ORDER BY row_id LIMIT {limit}"
)


def _percentiles(values: list[float]) -> dict:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}
    ordered = sorted(values)
    n = len(ordered)

    def at(q: float) -> float:
        return ordered[min(n - 1, int(q * (n - 1)))]

    return {"p50": at(0.50), "p95": at(0.95), "p99": at(0.99), "count": n}


def _load_transactions(settings, limit: int) -> list[Transaction]:
    rows = connect(settings).execute(_QUERY.format(limit=limit)).fetchall()
    return [
        Transaction(
            transaction_id=f"B{i}",
            step=int(r[0]),
            type=r[1],
            amount=float(r[2]),
            name_orig=r[3],
            old_balance_org=float(r[4]),
            name_dest=r[5],
            old_balance_dest=float(r[6]),
            is_flagged_fraud=bool(r[7]),
        )
        for i, r in enumerate(rows)
    ]


def _hardware() -> dict:
    import psutil

    info = {
        "cpu_cores": psutil.cpu_count(),
        "ram_total_mb": psutil.virtual_memory().total / 1e6,
    }
    try:
        import torch

        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["vram_total_mb"] = torch.cuda.get_device_properties(0).total_memory / 1e6
    except Exception:
        pass
    return info


def _build(settings):
    ml = MLDecisionProvider(settings)
    ml_loaded = ml.load()
    disabled = settings.model_copy(update={"laya_enabled": False, "laya_mode": "disabled"})
    graph = GraphContextProvider(settings)
    evidence = EvidenceEngine(settings, graph_provider=graph, ml=ml)
    engine = DecisionEngine(
        settings,
        evidence_engine=evidence,
        laya_engine=LayaDecisionEngine(disabled),
        state_builder=DecisionStateBuilder(settings),
    )
    return ml_loaded, ml, graph, evidence, engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=5000)
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.paysim_csv.exists():
        print("[error] ejecuta scripts/download_paysim.py primero")
        return 1

    transactions = _load_transactions(settings, args.records)
    ml_loaded, ml, graph, evidence, engine = _build(settings)
    print(f"[bench] ml_loaded={ml_loaded} registros={len(transactions)} batch={args.batch}")

    for tx in transactions[:50]:
        engine.decide(tx)

    stages = {key: [] for key in ("total_ms", "features_ms", "graph_ms", "rules_ms", "ml_ms", "state_ms")}
    t0 = time.perf_counter()
    for tx in transactions:
        result = engine.decide(tx)
        for key in stages:
            stages[key].append(getattr(result.latency, key))
    elapsed = time.perf_counter() - t0

    batched = []
    for i in range(0, len(transactions), args.batch):
        chunk = transactions[i:i + args.batch]
        start = time.perf_counter()
        for tx in chunk:
            engine.decide(tx)
        batched.append((time.perf_counter() - start) * 1000.0 / len(chunk))

    rules = RulesEngine(settings)
    rules_latency = []
    ml_latency = []
    graph_latency = []
    for tx in transactions:
        features, evidence_obj, _ = evidence.evaluate(tx)
        start = time.perf_counter()
        rules.evaluate(tx, evidence_obj.graph.context)
        rules_latency.append((time.perf_counter() - start) * 1000.0)

    # serialización de la respuesta
    serialization = []
    result = engine.decide(transactions[0])
    for _ in range(1000):
        start = time.perf_counter()
        result.model_dump(mode="json")
        serialization.append((time.perf_counter() - start) * 1000.0)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "records": len(transactions),
        "batch": args.batch,
        "throughput_tps": len(transactions) / elapsed,
        "stages_ms": {key: _percentiles(values) for key, values in stages.items()},
        "batching": {"per_item_ms": _percentiles(batched), "batch_size": args.batch},
        "components_ms": {
            "rules": _percentiles(rules_latency),
            "serialization": _percentiles(serialization),
        },
        "hardware": _hardware(),
        "note": "Batch offline por etapa; no incluye red. No es garantía de producción.",
    }

    settings.benchmarks_path.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (settings.benchmarks_path / f"e2e_{stamp}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (settings.benchmarks_path / "e2e_latest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    total = payload["stages_ms"]["total_ms"]
    print(
        f"[bench] total p50={total['p50']:.2f} p95={total['p95']:.2f} p99={total['p99']:.2f} ms "
        f"(n={total['count']}) tps={payload['throughput_tps']:.0f}"
    )
    for key in ("features_ms", "graph_ms", "rules_ms", "ml_ms", "state_ms"):
        stage = payload["stages_ms"][key]
        print(f"    {key:<12} p50={stage['p50']:.3f} p95={stage['p95']:.3f} p99={stage['p99']:.3f}")
    print(f"[bench] guardado en {settings.benchmarks_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

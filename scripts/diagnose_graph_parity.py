#!/usr/bin/env python3
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

"""Diagnóstico de paridad grafo online/offline (solo lectura).

Compara las seis features de grafo calculadas online (``GraphState`` con
los límites LRU configurados) contra las almacenadas offline (memmaps), y
resume la divergencia y la cardinalidad real frente a los caps.

No modifica datos: abre DuckDB y los memmaps en modo lectura.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import duckdb  # noqa: E402

from app.config import Settings  # noqa: E402
from app.data.paysim_db import DB_FILENAME  # noqa: E402
from app.features.graph_state import GraphState  # noqa: E402
from app.features.offline import read_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Paridad de features de grafo online vs offline.")
    parser.add_argument("--max-records", type=int, default=500_000)
    parser.add_argument("--all", action="store_true", help="recorre todo el dataset")
    args = parser.parse_args()

    settings = Settings()
    db_path = settings.processed_data_path / DB_FILENAME
    if not db_path.exists():
        print(json.dumps({"available": False, "reason": "sin base DuckDB"}, indent=2))
        return 1

    artifacts = read_artifacts(settings)
    features = artifacts.load_features(mode="r")

    conn = duckdb.connect(str(db_path), read_only=True)
    cardinality = conn.execute(
        "SELECT count(DISTINCT nameOrig), count(DISTINCT nameDest), "
        "count(DISTINCT (nameOrig || '->' || nameDest)) FROM transactions"
    ).fetchone()

    limit = artifacts.rows if args.all else min(args.max_records, artifacts.rows)
    cursor = conn.execute(
        f"SELECT step, nameOrig, nameDest FROM transactions ORDER BY row_id LIMIT {int(limit)}"
    )
    state = GraphState(settings.graph_max_accounts, settings.graph_max_edges)
    compared = divergent = 0
    first = None
    worst = 0.0
    while True:
        batch = cursor.fetchmany(10_000)
        if not batch:
            break
        for step, origin, dest in batch:
            index = compared
            context = state.context(origin, dest, int(step))
            online = [
                context.origin_degree_before,
                context.destination_degree_before,
                context.origin_unique_destinations_before,
                context.destination_unique_origins_before,
                context.edge_count_before,
                context.edge_seen_before,
            ]
            offline = [float(features[index][c]) for c in range(9, 15)]
            if online != offline:
                divergent += 1
                if first is None:
                    first = {"index": index, "online": online, "offline": offline}
                worst = max(worst, max(abs(a - b) for a, b in zip(online, offline)))
            state.observe(origin, dest, int(step))
            compared += 1

    conn.close()
    print(
        json.dumps(
            {
                "available": True,
                "compared": compared,
                "dataset_rows": artifacts.rows,
                "caps": {
                    "max_accounts": settings.graph_max_accounts,
                    "max_edges": settings.graph_max_edges,
                },
                "cardinality": {
                    "origins": int(cardinality[0]),
                    "destinations": int(cardinality[1]),
                    "edges": int(cardinality[2]),
                },
                "divergent": divergent,
                "divergence_rate": divergent / compared if compared else 0.0,
                "max_abs_diff": worst,
                "first_divergence": first,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

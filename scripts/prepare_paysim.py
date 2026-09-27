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

"""Construye la base DuckDB de PaySim y reporta split temporal + drift.

Uso:  .venv/bin/python scripts/prepare_paysim.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.data import build_database, drift_report, split_stats  # noqa: E402


def main() -> int:
    settings = get_settings()
    t0 = time.time()
    db_path = build_database(settings, force=False)
    print(f"[db] {db_path} ({time.time() - t0:.1f}s)")

    splits = split_stats(settings)
    drift = drift_report(settings)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "dataset": "paysim",
        "rows_total": sum(item["rows"] for item in splits),
        "splits": splits,
        "drift": drift,
    }

    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    out = settings.metrics_path / "splits.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[out] {out}")

    print(f"{'split':<12}{'steps':<14}{'rows':>10}{'fraud':>9}{'tasa':>12}")
    for item in splits:
        print(
            f"{item['split']:<12}{item['step_min']}-{item['step_max']:<8}"
            f"{item['rows']:>10}{item['fraud']:>9}{item['fraud_rate']:>12.6f}"
        )
    print("drift:", drift)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

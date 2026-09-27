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

"""Compara RF vs GBM (calidad + latencia) y recomienda el modelo servido.

Uso:  .venv/bin/python scripts/model_selection.py

Escribe `results/metrics/model_selection.json`. No modifica el modelo servido.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.training.model_selection import choose_winner, compare_models  # noqa: E402


def main() -> int:
    settings = get_settings()
    comparison = compare_models(settings)
    decision = choose_winner(comparison)
    payload = {**comparison, "decision": decision}

    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / "model_selection.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    for kind in ("rf", "gbm"):
        candidate = comparison["candidates"][kind]
        test = candidate["test"]
        latency = candidate["latency_ms"]
        print(
            f"[{kind}] thr={candidate['threshold']:.4f} "
            f"test P={test['precision']:.4f} R={test['recall']:.4f} F1={test['f1']:.4f} "
            f"PR-AUC={test['pr_auc']:.4f} | p95={latency['p95']:.3f} ms"
        )
    print(
        f"[decision] winner={decision['winner']} "
        f"(quality_win={decision['quality_win']} latency_ok={decision['latency_ok']} "
        f"gbm_p95={decision['gbm_p95_ms']:.3f} vs rf_p95={decision['rf_p95_ms']:.3f})"
    )
    print(f"[out] {settings.metrics_path / 'model_selection.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

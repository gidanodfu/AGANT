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

"""Genera la variante audit_only y la ablación online (± grafo).

Uso:  .venv/bin/python scripts/evaluate_variants.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.training.ablation import run_ablation  # noqa: E402
from app.training.audit_only import train_audit_only  # noqa: E402
from app.training.registry import append_experiment  # noqa: E402


def main() -> int:
    settings = get_settings()

    audit = train_audit_only(settings)
    print(
        f"[audit_only] P={audit['metrics']['precision']:.4f} R={audit['metrics']['recall']:.4f} "
        f"F1={audit['metrics']['f1']:.4f} (post-transacción, NO online)"
    )
    append_experiment(
        settings,
        {
            "kind": "audit_only",
            "dataset": "paysim",
            "split": "test",
            "threshold": 0.5,
            "feature_version": "audit_post_transaction",
            "model_version": "rf_audit_only",
            "metrics": audit["metrics"],
        },
    )

    ablation = run_ablation(settings)
    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / "ablation.json").write_text(
        json.dumps(ablation, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"[ablation] F1 sin grafo={ablation['online_without_graph']['metrics']['f1']:.4f} "
        f"con grafo={ablation['online_with_graph']['metrics']['f1']:.4f} "
        f"(delta={ablation['delta_f1']:+.4f})"
    )
    append_experiment(
        settings,
        {
            "kind": "ablation",
            "dataset": "paysim",
            "split": "validation",
            "threshold": 0.5,
            "feature_version": "online_v1",
            "model_version": "rf_ablation",
            "metrics": {"delta_f1": ablation["delta_f1"]},
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

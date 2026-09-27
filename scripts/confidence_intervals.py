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

"""Intervalos de confianza (bootstrap) del modelo servido sobre TEST.

Uso:  .venv/bin/python scripts/confidence_intervals.py [--n 1000]

Escribe `results/metrics/confidence_intervals.json`. No modifica el servicio.
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
from app.data.temporal_split import SplitName  # noqa: E402
from app.features import read_artifacts  # noqa: E402
from app.training.confidence import bootstrap_ci  # noqa: E402
from app.training.train_online import load_model, split_mask  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap de métricas TEST.")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    settings = get_settings()
    artifact = load_model(settings)
    artifacts = read_artifacts(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()

    mask = split_mask(steps, SplitName.TEST)
    x_test = np.asarray(features[mask], dtype=np.float32)
    y_test = np.asarray(labels[mask], dtype=np.int8)
    scores = artifact["model"].predict_proba(x_test)[:, 1]

    start = time.time()
    result = bootstrap_ci(y_test, scores, float(artifact["threshold"]), n=args.n, seed=args.seed)
    elapsed = time.time() - start

    payload = {
        "dataset": "paysim",
        "split": "test",
        "model_kind": artifact.get("model_kind"),
        "model_version": artifact["model_version"],
        "feature_version": artifact["feature_version"],
        "rows": int(y_test.shape[0]),
        "fraud": int(y_test.sum()),
        "elapsed_s": elapsed,
        **result,
    }
    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / "confidence_intervals.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    for key, summary in result["ci"].items():
        point = result["point"][key]
        print(
            f"[{key}] {point:.4f}  IC95=[{summary['low']:.4f}, {summary['high']:.4f}] "
            f"±{summary['std']:.4f}"
        )
    print(f"[out] {settings.metrics_path / 'confidence_intervals.json'} ({elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

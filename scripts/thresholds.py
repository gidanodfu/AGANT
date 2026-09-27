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

"""Selecciona el umbral sobre VALIDATION y registra el experimento.

Uso:  .venv/bin/python scripts/thresholds.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.data.temporal_split import SplitName  # noqa: E402
from app.features import load_meta, read_artifacts  # noqa: E402
from app.training.registry import append_experiment  # noqa: E402
from app.training.thresholds import select_threshold  # noqa: E402
from app.training.train_online import load_model, split_mask  # noqa: E402


def main() -> int:
    settings = get_settings()
    artifact = load_model(settings)
    model = artifact["model"]
    artifacts = read_artifacts(settings)
    features = artifacts.load_features()
    labels = artifacts.load_labels()
    steps = artifacts.load_steps()
    mask = split_mask(steps, SplitName.VALIDATION)
    x = np.asarray(features[mask], dtype=np.float32)
    y = np.asarray(labels[mask], dtype=np.int8)
    scores = model.predict_proba(x)[:, 1]

    result = select_threshold(y, scores, "f1")
    payload = {
        "dataset": "paysim",
        "split": "validation",
        "model_version": artifact["model_version"],
        "feature_version": artifact["feature_version"],
        "current_threshold": artifact["threshold"],
        **result,
    }
    settings.metrics_path.mkdir(parents=True, exist_ok=True)
    (settings.metrics_path / "threshold_analysis.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    append_experiment(
        settings,
        {
            "kind": "threshold_selection",
            "dataset": "paysim",
            "split": "validation",
            "threshold": result["best"]["threshold"],
            "feature_version": artifact["feature_version"],
            "model_version": artifact["model_version"],
            "metrics": result["best"],
        },
    )
    print(
        f"[thresholds] mejor f1={result['best']['f1']:.4f} en umbral={result['best']['threshold']} "
        f"(actual={artifact['threshold']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

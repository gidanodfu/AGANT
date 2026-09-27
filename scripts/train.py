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

"""Entrena el modelo online y lo evalúa en validation y test.

Uso:  .venv/bin/python scripts/train.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.data.temporal_split import SplitName  # noqa: E402
from app.training import evaluate_model, train_online  # noqa: E402

FIELDS = ("precision", "recall", "f1", "roc_auc", "pr_auc", "tp", "fp", "fn", "tn")


def _print(tag: str, metrics: dict) -> None:
    values = "  ".join(f"{key}={metrics.get(key)}" for key in FIELDS)
    print(f"[{tag}] {values}")


def main() -> int:
    settings = get_settings()
    trained = train_online(settings)
    print(f"[train] {trained['model_version']} en {trained['train_seconds']:.1f}s")
    _print("validation", trained["metrics"])

    for split in (SplitName.VALIDATION, SplitName.TEST):
        payload = evaluate_model(settings, split=split)
        _print(split.value, payload["metrics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

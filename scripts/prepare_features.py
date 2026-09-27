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

"""Genera los memmaps de features online (9 tabulares + 6 grafo) de PaySim.

Uso:  .venv/bin/python scripts/prepare_features.py [--force]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.features import build_features, load_meta  # noqa: E402


def main() -> int:
    force = "--force" in sys.argv
    settings = get_settings()
    t0 = time.time()
    artifacts = build_features(settings, force=force)
    meta = load_meta(settings)
    print(f"[features] {artifacts.features_path} {artifacts.rows} filas ({time.time() - t0:.1f}s)")
    print(f"[meta] version={meta['feature_version']} fraud={meta['fraud']} rate={meta['fraud_rate']:.6f}")
    print("[names]", ", ".join(meta["feature_names"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

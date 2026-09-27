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

"""Descarga idempotente de PaySim desde un espejo público de Hugging Face.

Uso:  .venv/bin/python scripts/download_paysim.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.data.paysim import HF_DATASET_REPO, HF_FILENAME, verify_paysim  # noqa: E402

EXPECTED_BYTES = 493_534_783


def main() -> int:
    settings = get_settings()
    target = settings.paysim_csv
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and target.stat().st_size > 0:
        print(f"[skip] {target} ya existe ({target.stat().st_size} bytes)")
    else:
        from huggingface_hub import hf_hub_download

        print(f"[download] {HF_DATASET_REPO}/{HF_FILENAME} -> {target}")
        downloaded = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename=HF_FILENAME,
            repo_type="dataset",
            local_dir=str(target.parent),
        )
        downloaded_path = Path(downloaded)
        if downloaded_path.resolve() != target.resolve():
            target.write_bytes(downloaded_path.read_bytes())
        print(f"[ok] {target} ({target.stat().st_size} bytes)")

    if target.stat().st_size != EXPECTED_BYTES:
        print(
            f"[warn] tamaño {target.stat().st_size} != esperado {EXPECTED_BYTES}; "
            "se verifica por contenido de todos modos."
        )

    stats = verify_paysim(target)
    print("[verify]", stats)
    if stats.rows != 6_362_620:
        print(f"[error] filas={stats.rows}, se esperaban 6,362,620")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

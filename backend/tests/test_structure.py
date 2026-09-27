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

"""Mantiene módulos pequeños y sin un orquestador monolítico."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "backend" / "app"
MAX_LINES = 350


def test_no_oversized_modules():
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        lines = path.read_text(encoding="utf-8").count("\n") + 1
        if lines > MAX_LINES:
            offenders.append((str(path.relative_to(REPO_ROOT)), lines))
    assert not offenders, f"módulos demasiado grandes: {offenders}"


def test_expected_layers_exist():
    for layer in ("contracts", "evidence", "decision", "events", "observability", "api", "ws", "replay"):
        assert (APP_DIR / layer).is_dir(), f"falta la capa {layer}"

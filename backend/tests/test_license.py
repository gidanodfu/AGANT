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

"""Verifica que el código propio lleve el aviso AGPL-3.0."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OWN_CODE_DIRS = [REPO_ROOT / "backend" / "app", REPO_ROOT / "frontend" / "src"]
MARKER = "GNU Affero General Public License"


def _own_files() -> list[Path]:
    files: list[Path] = []
    for directory in OWN_CODE_DIRS:
        files.extend(sorted(directory.rglob("*.py")))
        files.extend(sorted(directory.rglob("*.js")))
    return files


def test_every_own_source_has_agpl_header():
    missing = []
    for path in _own_files():
        head = path.read_text(encoding="utf-8")[:1500]
        if MARKER not in head:
            missing.append(str(path.relative_to(REPO_ROOT)))
    assert not missing, f"archivos sin aviso AGPL: {missing}"


def test_license_and_notice_exist():
    assert (REPO_ROOT / "LICENSE").exists()
    assert (REPO_ROOT / "NOTICE").exists()
    assert (REPO_ROOT / "THIRD_PARTY_NOTICES.md").exists()
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (REPO_ROOT / "LICENSE").read_text(encoding="utf-8").upper()

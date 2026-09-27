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

"""Verifica que el código y la configuración propios lleven el aviso AGPL-3.0."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKER = "GNU Affero General Public License"
CANONICAL = "This program is free software: you can redistribute it and/or modify"
REPO_URL = "https://github.com/gidanodfu/AGANT"

_SOURCE_TREES = (
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "backend" / "tests",
    REPO_ROOT / "scripts",
    REPO_ROOT / "frontend" / "src",
)
_SOURCE_GLOBS = ("*.py", "*.js", "*.sh")
_CONFIG_FILES = (
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "laya/Dockerfile.gpu",
    "frontend/nginx.conf",
    ".github/workflows/ci.yml",
    "docker-compose.yml",
    "pyproject.toml",
    "Makefile",
    "frontend/index.html",
    "frontend/styles/input.css",
    "laya/service/app.py",
)


def _own_files() -> list[Path]:
    files: list[Path] = []
    for tree in _SOURCE_TREES:
        for pattern in _SOURCE_GLOBS:
            files.extend(sorted(tree.rglob(pattern)))
    files.extend(REPO_ROOT / rel for rel in _CONFIG_FILES)
    return files


def test_every_own_file_has_canonical_agpl_header():
    missing = []
    for path in _own_files():
        head = path.read_text(encoding="utf-8")[:1500]
        if MARKER not in head or CANONICAL not in head or REPO_URL not in head:
            missing.append(str(path.relative_to(REPO_ROOT)))
    assert not missing, f"archivos sin aviso AGPL canónico: {missing}"


def test_license_and_notice_exist():
    assert (REPO_ROOT / "LICENSE").exists()
    assert (REPO_ROOT / "NOTICE").exists()
    assert (REPO_ROOT / "THIRD_PARTY_NOTICES.md").exists()
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (REPO_ROOT / "LICENSE").read_text(encoding="utf-8").upper()

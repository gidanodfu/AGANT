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

"""Servido del frontend estático (conveniencia para desarrollo).

En despliegue el frontend se sirve por separado (nginx). Aquí se monta
para poder ejecutar todo con un solo proceso.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, frontend: Path) -> bool:
    index = frontend / "index.html"
    if not index.exists():
        return False
    for name in ("src", "styles", "vendor", "assets"):
        directory = frontend / name
        if directory.exists():
            app.mount(f"/{name}", StaticFiles(directory=directory), name=f"frontend-{name}")

    @app.get("/", include_in_schema=False)
    async def _root() -> FileResponse:
        return FileResponse(index)

    @app.get("/home", include_in_schema=False)
    async def _home() -> FileResponse:
        return FileResponse(index)

    @app.get("/transacciones", include_in_schema=False)
    async def _transacciones() -> FileResponse:
        return FileResponse(index)

    @app.get("/decisiones", include_in_schema=False)
    async def _decisiones() -> FileResponse:
        return FileResponse(index)

    @app.get("/grafo", include_in_schema=False)
    async def _grafo() -> FileResponse:
        return FileResponse(index)

    @app.get("/nueva-transaccion", include_in_schema=False)
    async def _nueva_transaccion() -> FileResponse:
        return FileResponse(index)

    @app.get("/laya", include_in_schema=False)
    async def _laya() -> FileResponse:
        return FileResponse(index)

    return True

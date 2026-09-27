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

"""Escritura y lectura de matrices en ``numpy.memmap`` ``float32``.

Permite procesar PaySim por bloques sin cargar todo en RAM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class MemmapSpec:
    path: Path
    shape: tuple[int, ...]
    dtype: str = "float32"

    def open(self, mode: str = "r") -> npt.NDArray:
        return np.memmap(self.path, dtype=self.dtype, mode=mode, shape=self.shape)


def create(spec: MemmapSpec) -> npt.NDArray:
    spec.path.parent.mkdir(parents=True, exist_ok=True)
    return np.memmap(spec.path, dtype=spec.dtype, mode="w+", shape=spec.shape)


def write_rows(
    spec: MemmapSpec,
    row_slices: list[tuple[int, int]],
    fetcher,
    *,
    chunk_rows: int,
) -> int:
    """Escribe ``spec`` a partir de ``fetcher(offset, limit) -> secuencia de filas``.

    ``row_slices`` delimita las filas por bloque; ``fetcher`` debe devolver
    exactamente las filas pedidas. Devuelve el número de filas escritas.
    """
    data = create(spec)
    written = 0
    for start, end in row_slices:
        block_start = start
        while block_start < end:
            limit = min(chunk_rows, end - block_start)
            rows = fetcher(block_start, limit)
            block = np.asarray(rows, dtype=spec.dtype)
            if block.shape[0] != limit:
                raise ValueError(f"fetcher devolvió {block.shape[0]} filas, se esperaban {limit}")
            data[block_start:block_start + limit] = block
            written += limit
            block_start += limit
    data.flush()
    return written

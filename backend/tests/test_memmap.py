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

"""Tests de escritura/lectura de memmaps."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.data.memmap import MemmapSpec, write_rows


def test_write_rows_in_chunks(tmp_path: Path):
    spec = MemmapSpec(path=tmp_path / "x.dat", shape=(5, 3), dtype="float32")
    source = [[float(i), float(i * 2), float(i * 3)] for i in range(5)]

    def fetcher(offset: int, limit: int):
        return source[offset:offset + limit]

    written = write_rows(spec, [(0, 5)], fetcher, chunk_rows=2)
    assert written == 5
    data = np.memmap(spec.path, dtype="float32", mode="r", shape=(5, 3))
    assert data.dtype == np.float32
    assert data[4].tolist() == [4.0, 8.0, 12.0]

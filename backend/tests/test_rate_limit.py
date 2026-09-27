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

"""Tests del limitador de tasa en memoria."""

from __future__ import annotations

import pytest

from app.api import rate_limit
from app.errors import AGANTError


@pytest.fixture(autouse=True)
def _clean_buckets():
    rate_limit._BUCKETS.clear()
    yield
    rate_limit._BUCKETS.clear()


def test_limit_triggers_at_threshold():
    rate_limit._check("k", 2)
    rate_limit._check("k", 2)
    with pytest.raises(AGANTError):
        rate_limit._check("k", 2)


def test_buckets_are_bounded(monkeypatch):
    monkeypatch.setattr(rate_limit, "_MAX_BUCKETS", 3)
    for i in range(10):
        rate_limit._check(f"ip{i}:decision", 100)
    assert len(rate_limit._BUCKETS) <= 3

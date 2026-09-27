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

"""Tests de la división temporal."""

from __future__ import annotations

from app.data import SplitName, TemporalSplit, split_for_step


def test_boundaries():
    assert split_for_step(1) is SplitName.TRAIN
    assert split_for_step(520) is SplitName.TRAIN
    assert split_for_step(521) is SplitName.VALIDATION
    assert split_for_step(631) is SplitName.VALIDATION
    assert split_for_step(632) is SplitName.TEST
    assert split_for_step(743) is SplitName.TEST


def test_bounds_are_contiguous():
    split = TemporalSplit()
    assert split.bounds(SplitName.TRAIN) == (None, 520)
    assert split.bounds(SplitName.VALIDATION) == (521, 631)
    assert split.bounds(SplitName.TEST) == (632, None)
    assert set(split.describe()) == {"train", "validation", "test"}

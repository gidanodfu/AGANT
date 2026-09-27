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

"""Pipeline de datos offline de AGANT (PaySim)."""

from .paysim import (
    EXPECTED_COLUMNS,
    EXPECTED_ROWS,
    HF_DATASET_REPO,
    HF_FILENAME,
    PaySimStats,
    verify_paysim,
)
from .paysim_db import build_database, connect, drift_report, split_stats
from .temporal_split import SplitName, TemporalSplit, split_for_step

__all__ = [
    "EXPECTED_COLUMNS",
    "EXPECTED_ROWS",
    "HF_DATASET_REPO",
    "HF_FILENAME",
    "PaySimStats",
    "verify_paysim",
    "SplitName",
    "TemporalSplit",
    "split_for_step",
    "build_database",
    "connect",
    "drift_report",
    "split_stats",
]

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

"""Tests de verificación e ingesta de PaySim (con CSV mínimo)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.data import build_database, drift_report, split_stats, verify_paysim
from app.data.paysim import (
    EXPECTED_COLUMNS,
    GROUND_TRUTH_COLUMNS,
    POST_TRANSACTION_COLUMNS,
)

HEADER = ",".join(EXPECTED_COLUMNS)


def _row(step: int, name_orig: str, name_dest: str, amount: float, fraud: int) -> str:
    return f"{step},TRANSFER,{amount},{name_orig},100.0,0.0,{name_dest},0.0,0.0,{fraud},0"


def _write_csv(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_ground_truth_is_not_a_feature_column_constant():
    assert GROUND_TRUTH_COLUMNS == frozenset({"isFraud"})
    assert "newbalanceOrig" in POST_TRANSACTION_COLUMNS
    assert "isFraud" not in POST_TRANSACTION_COLUMNS


def test_verify_paysim_counts(tmp_path: Path):
    csv = tmp_path / "paysim.csv"
    _write_csv(csv, [
        _row(10, "C1", "M1", 10.0, 0),
        _row(600, "C2", "C3", 20.0, 1),
        _row(700, "C4", "M2", 30.0, 0),
    ])
    stats = verify_paysim(csv)
    assert stats.rows == 3
    assert stats.fraud == 1
    assert stats.columns == EXPECTED_COLUMNS


def test_verify_paysim_rejects_wrong_schema(tmp_path: Path):
    csv = tmp_path / "bad.csv"
    csv.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        verify_paysim(csv)


def test_build_database_and_split_stats(tmp_path: Path):
    settings = Settings(data_dir=str(tmp_path / "data"), results_dir=str(tmp_path / "res"))
    csv = settings.raw_data_path / "paysim.csv"
    _write_csv(csv, [
        _row(1, "C1", "M1", 10.0, 0),
        _row(520, "C2", "M2", 11.0, 0),
        _row(521, "C3", "C4", 20.0, 1),
        _row(631, "C5", "M3", 21.0, 0),
        _row(632, "C6", "C7", 30.0, 1),
    ])
    db = build_database(settings, force=True)
    assert db.exists()
    stats = {item["split"]: item for item in split_stats(settings)}
    assert stats["train"]["rows"] == 2
    assert stats["validation"]["rows"] == 2
    assert stats["test"]["rows"] == 1
    assert stats["validation"]["fraud"] == 1
    drift = drift_report(settings, min_step_rows=1)
    assert drift["steps"] == 5
    assert drift["steps_with_fraud"] == 2

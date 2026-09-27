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

"""Ingesta y verificación de PaySim.

``isFraud`` es ground truth: se usa para entrenamiento, evaluación,
métricas y drift; **nunca** como feature de inferencia online.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

HF_DATASET_REPO = "theman10/paysim"
HF_FILENAME = "paysim.csv"

EXPECTED_ROWS = 6_362_620

EXPECTED_COLUMNS: tuple[str, ...] = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)

GROUND_TRUTH_COLUMNS: frozenset[str] = frozenset({"isFraud"})
POST_TRANSACTION_COLUMNS: frozenset[str] = frozenset(
    {"newbalanceOrig", "newbalanceDest"}
)


@dataclass(frozen=True)
class PaySimStats:
    rows: int
    columns: tuple[str, ...]
    fraud: int
    flagged_fraud: int

    @property
    def fraud_rate(self) -> float:
        return self.fraud / self.rows if self.rows else 0.0


def read_header(csv_path: Path) -> tuple[str, ...]:
    import csv

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(next(csv.reader(handle)))


def verify_paysim(csv_path: Path, *, full_scan: bool = True) -> PaySimStats:
    """Verifica columnas y cuenta filas/fraudes; falla si el esquema no coincide."""
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    header = read_header(csv_path)
    if header != EXPECTED_COLUMNS:
        raise ValueError(f"columnas inesperadas en PaySim: {header}")

    if not full_scan:
        return PaySimStats(rows=0, columns=header, fraud=0, flagged_fraud=0)

    import duckdb

    query = f"""
        SELECT count(*) AS rows,
               sum(isFraud) AS fraud,
               sum(isFlaggedFraud) AS flagged
        FROM read_csv_auto('{csv_path.as_posix()}', header=true)
    """
    rows, fraud, flagged = duckdb.connect().execute(query).fetchone()
    return PaySimStats(
        rows=int(rows),
        columns=header,
        fraud=int(fraud),
        flagged_fraud=int(flagged),
    )

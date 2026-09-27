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

"""Base DuckDB de PaySim y estadísticas de división temporal."""

from __future__ import annotations

from pathlib import Path

import duckdb

from ..config import Settings
from .temporal_split import TRAIN_END, VALIDATION_END

DB_FILENAME = "paysim.duckdb"

_SPLIT_CASE = (
    f"CASE WHEN step <= {TRAIN_END} THEN 'train' "
    f"WHEN step <= {VALIDATION_END} THEN 'validation' ELSE 'test' END"
)


def connect(settings: Settings) -> duckdb.DuckDBPyConnection:
    settings.processed_data_path.mkdir(parents=True, exist_ok=True)
    (settings.processed_data_path / "tmp").mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(settings.processed_data_path / DB_FILENAME))
    conn.execute("PRAGMA threads=8")
    conn.execute("PRAGMA memory_limit='4GB'")
    conn.execute(f"PRAGMA temp_directory='{(settings.processed_data_path / 'tmp').as_posix()}'")
    return conn


def build_database(settings: Settings, *, force: bool = False) -> Path:
    """Crea la tabla ``transactions`` desde el CSV si aún no existe."""
    conn = connect(settings)
    exists = conn.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name='transactions'"
    ).fetchone()[0]
    if exists and not force:
        return settings.processed_data_path / DB_FILENAME

    csv = settings.paysim_csv.as_posix()
    conn.execute("DROP TABLE IF EXISTS transactions")
    conn.execute(
        f"""
        CREATE TABLE transactions AS
        SELECT row_number() OVER () AS row_id, *
        FROM read_csv_auto('{csv}', header=true)
        """
    )
    return settings.processed_data_path / DB_FILENAME


def split_stats(settings: Settings) -> list[dict]:
    conn = connect(settings)
    rows = conn.execute(
        f"""
        SELECT {_SPLIT_CASE} AS split,
               min(step) AS step_min, max(step) AS step_max,
               count(*) AS rows, sum(isFraud) AS fraud,
               avg(isFraud)::DOUBLE AS fraud_rate
        FROM transactions GROUP BY 1
        """
    ).fetchall()
    order = {"train": 0, "validation": 1, "test": 2}
    result = [
        {
            "split": r[0],
            "step_min": int(r[1]),
            "step_max": int(r[2]),
            "rows": int(r[3]),
            "fraud": int(r[4]),
            "fraud_rate": float(r[5]),
        }
        for r in rows
    ]
    return sorted(result, key=lambda item: order[item["split"]])


def drift_report(settings: Settings, *, min_step_rows: int = 100) -> dict:
    """Resumen de drift temporal de la tasa de fraude por ``step``.

    Las tasas por paso se restringen a pasos con al menos ``min_step_rows``
    filas para no reportar tasas ruidosas de denominadores diminutos.
    """
    conn = connect(settings)
    per_step = conn.execute(
        """
        SELECT step, count(*) AS rows, sum(isFraud) AS fraud
        FROM transactions GROUP BY step ORDER BY step
        """
    ).fetchall()
    rates = sorted(f / n for _, n, f in per_step if n >= min_step_rows)
    mid = len(per_step) // 2
    early = conn.execute(
        f"SELECT avg(isFraud)::DOUBLE FROM transactions WHERE step <= {per_step[mid][0]}"
    ).fetchone()[0]
    late = conn.execute(
        f"SELECT avg(isFraud)::DOUBLE FROM transactions WHERE step > {per_step[mid][0]}"
    ).fetchone()[0]

    def pct(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, int(q * (len(values) - 1)))
        return values[index]

    return {
        "steps": len(per_step),
        "steps_with_fraud": sum(1 for _, _, f in per_step if f),
        "min_step_rows": min_step_rows,
        "rate_p10": pct(rates, 0.10),
        "rate_p50": pct(rates, 0.50),
        "rate_p90": pct(rates, 0.90),
        "early_rate": float(early or 0.0),
        "late_rate": float(late or 0.0),
        "note": "La variación temporal de la tasa de fraude en PaySim es un fenómeno del dataset, no comportamiento de producción.",
    }

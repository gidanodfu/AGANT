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

"""Construcción offline de las 15 features online hacia memmaps float32.

Las seis features de grafo son **causales**: usan ``RANGE BETWEEN
UNBOUNDED PRECEDING AND 1 PRECEDING`` sobre ``step``, de modo que el
contexto es estrictamente de pasos anteriores. No se inventa un orden
interno dentro de un mismo ``step``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..config import Settings
from ..contracts.transaction import MODEL_FEATURE_NAMES
from ..data.paysim_db import connect

FEATURE_VERSION = "online_v1"

_GRAPH_WINDOW = "RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING"

_FEATURE_QUERY = f"""
WITH base AS (
  SELECT row_id, step, isFraud,
         amount, oldbalanceOrg, oldbalanceDest, type, nameOrig, nameDest,
         count(*) OVER (PARTITION BY nameOrig ORDER BY step {_GRAPH_WINDOW}) AS origin_degree_before,
         count(*) OVER (PARTITION BY nameDest ORDER BY step {_GRAPH_WINDOW}) AS destination_degree_before,
         count(DISTINCT nameDest) OVER (PARTITION BY nameOrig ORDER BY step {_GRAPH_WINDOW}) AS origin_unique_destinations_before,
         count(DISTINCT nameOrig) OVER (PARTITION BY nameDest ORDER BY step {_GRAPH_WINDOW}) AS destination_unique_origins_before,
         count(*) OVER (PARTITION BY nameOrig, nameDest ORDER BY step {_GRAPH_WINDOW}) AS edge_count_before
  FROM transactions
)
SELECT row_id, step, isFraud,
       step::DOUBLE AS f_step,
       amount::DOUBLE AS f_amount,
       oldbalanceOrg::DOUBLE AS f_origin_old_balance,
       oldbalanceDest::DOUBLE AS f_destination_old_balance,
       (type = 'CASH_IN')::INT AS type_CASH_IN,
       (type = 'CASH_OUT')::INT AS type_CASH_OUT,
       (type = 'DEBIT')::INT AS type_DEBIT,
       (type = 'PAYMENT')::INT AS type_PAYMENT,
       (type = 'TRANSFER')::INT AS type_TRANSFER,
       origin_degree_before, destination_degree_before,
       origin_unique_destinations_before, destination_unique_origins_before,
       edge_count_before,
       CASE WHEN edge_count_before > 0 THEN 1 ELSE 0 END AS edge_seen_before
FROM base
ORDER BY row_id
"""


@dataclass(frozen=True)
class FeatureArtifacts:
    directory: Path
    rows: int

    @property
    def features_path(self) -> Path:
        return self.directory / "features.f32"

    @property
    def labels_path(self) -> Path:
        return self.directory / "labels.u8"

    @property
    def steps_path(self) -> Path:
        return self.directory / "steps.i16"

    @property
    def meta_path(self) -> Path:
        return self.directory / "meta.json"

    def load_features(self, mode: str = "r") -> np.ndarray:
        return np.memmap(self.features_path, dtype="float32", mode=mode, shape=(self.rows, 15))

    def load_labels(self, mode: str = "r") -> np.ndarray:
        return np.memmap(self.labels_path, dtype="uint8", mode=mode, shape=(self.rows,))

    def load_steps(self, mode: str = "r") -> np.ndarray:
        return np.memmap(self.steps_path, dtype="int16", mode=mode, shape=(self.rows,))


def _memmap(path: Path, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    path.parent.mkdir(parents=True, exist_ok=True)
    return np.memmap(path, dtype=dtype, mode="w+", shape=shape)


def build_features(settings: Settings, *, force: bool = False) -> FeatureArtifacts:
    """Genera los memmaps de features/labels/steps para todo PaySim."""
    directory = settings.processed_data_path / "paysim"
    directory.mkdir(parents=True, exist_ok=True)
    meta_path = directory / "meta.json"

    conn = connect(settings)
    total = int(conn.execute("SELECT count(*) FROM transactions").fetchone()[0])
    artifacts = FeatureArtifacts(directory=directory, rows=total)
    if artifacts.meta_path.exists() and not force:
        return artifacts

    features = _memmap(artifacts.features_path, "float32", (total, 15))
    labels = _memmap(artifacts.labels_path, "uint8", (total,))
    steps = _memmap(artifacts.steps_path, "int16", (total,))

    cursor = conn.execute(_FEATURE_QUERY)
    offset = 0
    chunk = int(settings.chunk_rows)
    while True:
        rows = cursor.fetchmany(chunk)
        if not rows:
            break
        array = np.asarray(rows, dtype=np.float64)
        # columnas 0=row_id, 1=step, 2=isFraud, 3..17 = features
        n = array.shape[0]
        features[offset:offset + n] = array[:, 3:18].astype(np.float32)
        labels[offset:offset + n] = array[:, 2].astype(np.uint8)
        steps[offset:offset + n] = array[:, 1].astype(np.int16)
        offset += n

    if offset != total:
        raise RuntimeError(f"se escribieron {offset} filas, se esperaban {total}")

    features.flush()
    labels.flush()
    steps.flush()

    fraud = int(labels.sum())
    meta = {
        "feature_version": FEATURE_VERSION,
        "rows": total,
        "feature_names": list(MODEL_FEATURE_NAMES),
        "fraud": fraud,
        "fraud_rate": fraud / total,
        "graph_window": _GRAPH_WINDOW,
        "files": {
            "features": artifacts.features_path.name,
            "labels": artifacts.labels_path.name,
            "steps": artifacts.steps_path.name,
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return artifacts


def load_meta(settings: Settings) -> dict:
    return json.loads((settings.processed_data_path / "paysim" / "meta.json").read_text("utf-8"))


def read_artifacts(settings: Settings) -> FeatureArtifacts:
    """Carga la referencia a los memmaps ya generados (requiere ``meta.json``)."""
    meta = load_meta(settings)
    return FeatureArtifacts(
        directory=settings.processed_data_path / "paysim",
        rows=int(meta["rows"]),
    )

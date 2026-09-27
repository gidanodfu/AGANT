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

Las seis features de grafo se calculan con el **mismo** ``GraphState`` que
usa la ruta online, con los mismos límites LRU de configuración. Así el
entrenamiento y el servicio comparten exactamente la misma definición de
contexto: la paridad es por construcción, no por coincidencia.

El contexto es causal: ``GraphState`` sólo ve pasos estrictamente anteriores
y difiere las actualizaciones del ``step`` en curso.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..config import Settings
from ..contracts.transaction import MODEL_FEATURE_NAMES
from ..data.paysim_db import connect
from .graph_state import GraphState

# La definición de features cambió (grafo acotado idéntico a online): nueva
# versión para no reutilizar modelos entrenados con la versión anterior.
FEATURE_VERSION = "online_v2"

_GRAPH_SEMANTICS = "GraphState online causal con LRU de cuentas/aristas"

_TYPE_ORDER = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")

# Columnas 3..17 del vector: 9 tabulares + 6 de grafo (MODEL_FEATURE_NAMES).
_TABULAR_QUERY = """
SELECT row_id, step, isFraud,
       amount, oldbalanceOrg, oldbalanceDest, type, nameOrig, nameDest
FROM transactions
ORDER BY row_id
"""


def _one_hot(transaction_type: str) -> list[float]:
    return [1.0 if transaction_type == name else 0.0 for name in _TYPE_ORDER]


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

    state = GraphState(settings.graph_max_accounts, settings.graph_max_edges)
    cursor = conn.execute(_TABULAR_QUERY)
    offset = 0
    chunk = int(settings.chunk_rows)
    while True:
        rows = cursor.fetchmany(chunk)
        if not rows:
            break
        n = len(rows)
        block = np.empty((n, 15), dtype=np.float32)
        labels_block = np.empty((n,), dtype=np.uint8)
        steps_block = np.empty((n,), dtype=np.int16)
        for i, row in enumerate(rows):
            _, step, is_fraud, amount, ob_org, ob_dest, ttype, orig, dest = row
            step = int(step)
            state.advance(step)
            context = state.context(orig, dest)
            block[i, 0] = step
            block[i, 1] = amount
            block[i, 2] = ob_org
            block[i, 3] = ob_dest
            block[i, 4:9] = _one_hot(ttype)
            block[i, 9] = context.origin_degree_before
            block[i, 10] = context.destination_degree_before
            block[i, 11] = context.origin_unique_destinations_before
            block[i, 12] = context.destination_unique_origins_before
            block[i, 13] = context.edge_count_before
            block[i, 14] = context.edge_seen_before
            labels_block[i] = is_fraud
            steps_block[i] = step
            state.observe(orig, dest, step)
        features[offset:offset + n] = block
        labels[offset:offset + n] = labels_block
        steps[offset:offset + n] = steps_block
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
        "graph_window": _GRAPH_SEMANTICS,
        "graph_caps": {
            "max_accounts": settings.graph_max_accounts,
            "max_edges": settings.graph_max_edges,
        },
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

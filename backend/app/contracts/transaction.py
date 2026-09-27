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

"""Contratos de transacción, features de inferencia y contexto de grafo.

La ruta online sólo admite información disponible *antes* de decidir.
Quedan prohibidos como features: ``newbalanceOrg``, ``newbalanceDest``,
``isFraud`` y cualquier campo derivado después de completar la operación.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

ML_FEATURE_NAMES: tuple[str, ...] = (
    "step",
    "amount",
    "origin_old_balance",
    "destination_old_balance",
    "type_CASH_IN",
    "type_CASH_OUT",
    "type_DEBIT",
    "type_PAYMENT",
    "type_TRANSFER",
)

GRAPH_FEATURE_NAMES: tuple[str, ...] = (
    "origin_degree_before",
    "destination_degree_before",
    "origin_unique_destinations_before",
    "destination_unique_origins_before",
    "edge_count_before",
    "edge_seen_before",
)

MODEL_FEATURE_NAMES: tuple[str, ...] = ML_FEATURE_NAMES + GRAPH_FEATURE_NAMES


class TransactionType(str, Enum):
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    DEBIT = "DEBIT"
    PAYMENT = "PAYMENT"
    TRANSFER = "TRANSFER"


class Transaction(BaseModel):
    """Evento de entrada a la decisión online (campos causales)."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=128)
    step: int = Field(ge=0)
    type: TransactionType
    amount: float = Field(ge=0)
    name_orig: str = Field(min_length=1, max_length=128)
    old_balance_org: float = Field(ge=0)
    name_dest: str = Field(min_length=1, max_length=128)
    old_balance_dest: float = Field(ge=0)
    # Señal del protocolo de inferencia (no es ground truth). Opcional.
    is_flagged_fraud: bool = False


class InferenceFeatures(BaseModel):
    """Vector de 15 features del modelo online: 9 tabulares + 6 de grafo."""

    model_config = ConfigDict(extra="forbid")

    step: float
    amount: float
    origin_old_balance: float
    destination_old_balance: float
    type_CASH_IN: float = 0.0
    type_CASH_OUT: float = 0.0
    type_DEBIT: float = 0.0
    type_PAYMENT: float = 0.0
    type_TRANSFER: float = 0.0

    origin_degree_before: float = 0.0
    destination_degree_before: float = 0.0
    origin_unique_destinations_before: float = 0.0
    destination_unique_origins_before: float = 0.0
    edge_count_before: float = 0.0
    edge_seen_before: float = 0.0

    def as_vector(self) -> list[float]:
        return [float(getattr(self, name)) for name in MODEL_FEATURE_NAMES]

    @field_validator("amount", "origin_old_balance", "destination_old_balance")
    @classmethod
    def _finite(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("los importes deben ser finitos")
        return value


class GraphContext(BaseModel):
    """Las seis features de contexto de grafo, causales respecto de la transacción."""

    model_config = ConfigDict(extra="forbid")

    origin_degree_before: int = Field(default=0, ge=0)
    destination_degree_before: int = Field(default=0, ge=0)
    origin_unique_destinations_before: int = Field(default=0, ge=0)
    destination_unique_origins_before: int = Field(default=0, ge=0)
    edge_count_before: int = Field(default=0, ge=0)
    edge_seen_before: int = Field(default=0, ge=0)

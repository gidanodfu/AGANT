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

"""Tests del feature builder online."""

from __future__ import annotations

from app.contracts.transaction import (
    MODEL_FEATURE_NAMES,
    GraphContext,
    InferenceFeatures,
    Transaction,
)
from app.features.feature_builder import FeatureBuilder


def _transaction(**overrides) -> Transaction:
    base = dict(
        transaction_id="T1",
        step=100,
        type="TRANSFER",
        amount=5000.0,
        name_orig="C1",
        old_balance_org=5000.0,
        name_dest="M1",
        old_balance_dest=0.0,
    )
    base.update(overrides)
    return Transaction(**base)


def test_build_matches_model_feature_order():
    graph = GraphContext(origin_degree_before=3, destination_degree_before=2,
                         origin_unique_destinations_before=3,
                         destination_unique_origins_before=2,
                         edge_count_before=1, edge_seen_before=1)
    features = FeatureBuilder().build(_transaction(), graph)
    assert isinstance(features, InferenceFeatures)
    vector = features.as_vector()
    assert len(vector) == len(MODEL_FEATURE_NAMES) == 15
    assert features.type_TRANSFER == 1.0
    assert features.type_PAYMENT == 0.0
    assert features.destination_degree_before == 2.0


def test_one_hot_is_exclusive():
    graph = GraphContext()
    for tx_type in ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"):
        features = FeatureBuilder().build(_transaction(type=tx_type), graph)
        assert sum(features.as_vector()[4:9]) == 1.0

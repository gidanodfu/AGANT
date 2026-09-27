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

"""Tests de los contratos tipados."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts import (
    MODEL_FEATURE_NAMES,
    ApiResponse,
    ErrorCode,
    ErrorResponse,
    Event,
    EventType,
    InferenceFeatures,
    Source,
    Transaction,
    TransactionType,
)


def _transaction(**overrides) -> dict:
    base = dict(
        transaction_id="T1",
        step=1,
        type="TRANSFER",
        amount=100.0,
        name_orig="C1",
        old_balance_org=100.0,
        name_dest="M1",
        old_balance_dest=0.0,
    )
    base.update(overrides)
    return base


def test_feature_vector_has_15_in_declared_order():
    features = InferenceFeatures(step=1, amount=10.0, origin_old_balance=5.0, destination_old_balance=0.0)
    vector = features.as_vector()
    assert len(vector) == 15
    assert len(MODEL_FEATURE_NAMES) == 15
    assert vector[0] == 1.0 and vector[1] == 10.0


def test_transaction_rejects_negative_amount_and_extra_fields():
    with pytest.raises(ValidationError):
        Transaction(**_transaction(amount=-1.0))
    with pytest.raises(ValidationError):
        Transaction(**_transaction(isFraud=True))


def test_transaction_does_not_carry_ground_truth_by_default():
    tx = Transaction(**_transaction())
    assert tx.is_flagged_fraud is False
    assert not hasattr(tx, "newbalance_org")


def test_event_identity_distinguishes_live_and_replay():
    live = Event.create(EventType.DECISION_CREATED, Source.LIVE, 1, "T1")
    replay = Event.create(EventType.DECISION_CREATED, Source.REPLAY, 2, "T1")
    assert live.event_id != replay.event_id
    assert live.event_id == "live:decision.created:T1"
    assert replay.event_id == "replay:decision.created:T1"


def test_api_response_ok_and_fail():
    ok = ApiResponse[int].ok(7, request_id="r1")
    assert ok.success and ok.data == 7 and ok.error is None
    error = ErrorResponse(code=ErrorCode.ML_ERROR, message="no disponible")
    fail = ApiResponse[int].fail(error, request_id="r2")
    assert not fail.success and fail.data is None and fail.error is error


def test_transaction_type_enum_roundtrip():
    tx = Transaction(**_transaction(type="CASH_OUT"))
    assert tx.type is TransactionType.CASH_OUT

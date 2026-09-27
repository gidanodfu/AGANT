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

"""Tests de la taxonomía y del gestor de errores."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from app.contracts import ErrorCode, Severity
from app.errors import (
    HTTP_STATUS,
    SAFE_MESSAGES,
    AGANTError,
    ErrorManager,
    LayaError,
    TimeoutError_,
    ValidationError,
)


def test_classify_known_and_unknown():
    manager = ErrorManager()
    assert manager.classify(LayaError("x")).code is ErrorCode.LAYA_ERROR
    assert manager.classify(RuntimeError("boom")).code is ErrorCode.INTERNAL_ERROR
    assert manager.classify(TimeoutError()).code is ErrorCode.TIMEOUT_ERROR


def test_classify_pydantic_validation():
    manager = ErrorManager()
    try:
        from app.contracts import Transaction

        Transaction(transaction_id="", step=-1, type="X", amount=-1,
                    name_orig="", old_balance_org=-1, name_dest="", old_balance_dest=-1)
    except PydanticValidationError as exc:
        assert manager.classify(exc).code is ErrorCode.VALIDATION_ERROR


def test_error_response_is_safe_and_hides_details():
    manager = ErrorManager()
    secret = "/home/usuario/.secrets/token=abc123"
    response = manager.error_response(RuntimeError(secret))
    assert response.code is ErrorCode.INTERNAL_ERROR
    assert secret not in response.message
    assert response.message == SAFE_MESSAGES[ErrorCode.INTERNAL_ERROR]
    assert response.details is None


def test_taxonomy_has_status_and_severity_for_every_code():
    for code in ErrorCode:
        error = AGANTError("x", code=code)
        assert error.status == HTTP_STATUS[code]
        assert error.operation is None


def test_timeout_and_validation_status_codes():
    assert AGANTError("x", code=ErrorCode.TIMEOUT_ERROR).status == 504
    assert ValidationError("x").status == 400
    assert TimeoutError_("x").status == 504
    assert LayaError("x").severity is Severity.RECOVERABLE

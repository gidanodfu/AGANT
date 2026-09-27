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

"""Rate limiting simple en memoria (ventana deslizante por IP).

# ponytail: por proceso; usar Redis o un limitador distribuido si hay
# varias réplicas o ataques reales.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request

from ..contracts.enums import ErrorCode, Severity
from ..errors import AGANTError

_BUCKETS: dict[str, deque] = defaultdict(deque)
_WINDOW_S = 60.0


def _check(key: str, limit: int) -> None:
    now = time.monotonic()
    bucket = _BUCKETS[key]
    while bucket and now - bucket[0] > _WINDOW_S:
        bucket.popleft()
    if len(bucket) >= limit:
        raise AGANTError(
            f"rate limit excedido para {key}",
            code=ErrorCode.VALIDATION_ERROR,
            status=429,
            severity=Severity.WARNING,
            public_message="Demasiadas solicitudes. Intenta de nuevo en unos segundos.",
        )
    bucket.append(now)


def _client(request: Request) -> str:
    return request.client.host if request.client else "desconocido"


def rate_limit_decision(request: Request) -> None:
    _check(f"decision:{_client(request)}", request.app.state.settings.rate_limit_decision_per_min)


def rate_limit_flow(request: Request) -> None:
    _check(f"flow:{_client(request)}", request.app.state.settings.rate_limit_flow_per_min)

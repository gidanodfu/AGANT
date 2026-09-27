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

"""Contrato de evento con identidad única y secuencia."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import EventType, Source


def build_event_id(source: Source, event_type: EventType, transaction_id: str) -> str:
    """Identidad de evento que distingue ``live`` de ``replay`` para un mismo id."""
    return f"{source.value}:{event_type.value}:{transaction_id}"


class Event(BaseModel):
    """Evento interno/publicable. ``event_id`` no deduplica sólo por transacción."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: EventType
    source: Source
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sequence: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: EventType,
        source: Source,
        sequence: int,
        transaction_id: str,
        payload: dict[str, Any] | None = None,
    ) -> "Event":
        return cls(
            event_id=build_event_id(source, event_type, transaction_id),
            event_type=event_type,
            source=source,
            sequence=sequence,
            payload=payload or {},
        )

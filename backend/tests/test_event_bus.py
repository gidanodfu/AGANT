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

"""Tests del EventBus, incluida la política de backpressure."""

from __future__ import annotations

import asyncio

from app.contracts import Event, EventType, Source
from app.events import EventBus


def _event(bus: EventBus, tx: str = "T1") -> Event:
    return Event.create(EventType.DECISION_CREATED, Source.LIVE, bus.next_sequence(), tx)


def test_sequence_and_delivery():
    bus = EventBus()
    queue = bus.subscribe()
    bus.publish(_event(bus))
    received = asyncio.run(queue.get())
    assert received.event_type is EventType.DECISION_CREATED
    assert received.sequence == 1
    assert bus.stats()["events_published"] == 1


def test_backpressure_drops_oldest_and_counts():
    bus = EventBus(subscriber_queue=2)
    queue = bus.subscribe()
    for i in range(5):
        bus.publish(_event(bus, f"T{i}"))
    assert queue.qsize() == 2
    assert bus.events_dropped == 3
    stats = bus.stats()
    assert stats["queue_depth"] == 2
    assert stats["events_published"] == 5


def test_unsubscribe_stops_delivery():
    bus = EventBus()
    queue = bus.subscribe()
    bus.unsubscribe(queue)
    bus.publish(_event(bus))
    assert bus.subscribers == 0


def test_drops_accumulate_across_subscribers():
    bus = EventBus(subscriber_queue=2)
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    for i in range(5):
        bus.publish(_event(bus, f"T{i}"))
    assert q1.qsize() == 2 and q2.qsize() == 2
    # contador global: 3 descartes por cada suscriptor
    assert bus.events_dropped == 6

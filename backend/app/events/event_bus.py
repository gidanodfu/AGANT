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

"""EventBus interno con backpressure y métricas explícitas.

Ante saturación aplica política *drop-oldest* por suscriptor y **cuenta**
las pérdidas; nunca se ocultan. Uso desde el bucle de eventos (sin locks).
"""

from __future__ import annotations

import asyncio
import itertools
import time

from ..contracts.events import Event


class EventBus:
    def __init__(self, max_queue: int = 1000, subscriber_queue: int = 2000) -> None:
        self.max_queue = max_queue
        self.subscriber_queue = subscriber_queue
        self._subscribers: set[asyncio.Queue] = set()
        self._sequence = itertools.count(1)
        self.events_published = 0
        self.events_dropped = 0
        self._publish_latencies: list[float] = []

    def next_sequence(self) -> int:
        return next(self._sequence)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.subscriber_queue)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    @property
    def subscribers(self) -> int:
        return len(self._subscribers)

    @property
    def queue_depth(self) -> int:
        return max((q.qsize() for q in self._subscribers), default=0)

    def publish(self, event: Event) -> bool:
        start = time.perf_counter()
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                    self.events_dropped += 1
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self.events_dropped += 1
        self.events_published += 1
        latency = (time.perf_counter() - start) * 1000.0
        self._publish_latencies.append(latency)
        if len(self._publish_latencies) > 2048:
            del self._publish_latencies[:1024]
        return True

    def publish_latency_ms(self) -> tuple[float, float]:
        if not self._publish_latencies:
            return 0.0, 0.0
        values = sorted(self._publish_latencies)
        return values[len(values) // 2], values[min(len(values) - 1, int(0.95 * len(values)))]

    def stats(self) -> dict:
        p50, p95 = self.publish_latency_ms()
        return {
            "events_published": self.events_published,
            "events_dropped": self.events_dropped,
            "queue_depth": self.queue_depth,
            "subscribers": self.subscribers,
            "publish_latency_p50_ms": p50,
            "publish_latency_p95_ms": p95,
        }

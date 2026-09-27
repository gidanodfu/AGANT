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

"""EventBus interno con backpressure y métricas explícitas.

Ante saturación aplica política *drop-oldest* por suscriptor y **cuenta**
las pérdidas; nunca se ocultan. Uso desde el bucle de eventos (sin locks).
"""

from __future__ import annotations

import asyncio
import itertools
import time
from collections import deque

from ..contracts.events import Event


class EventBus:
    def __init__(self, subscriber_queue: int = 2000, history_size: int = 1000) -> None:
        self.subscriber_queue = subscriber_queue
        self._subscribers: set[asyncio.Queue] = set()
        self._drops_by_subscriber: dict[asyncio.Queue, int] = {}
        self._history: deque[Event] = deque(maxlen=max(0, history_size))
        self._sequence = itertools.count(1)
        self.events_published = 0
        self.events_dropped = 0
        self._publish_latencies: list[float] = []

    def next_sequence(self) -> int:
        return next(self._sequence)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.subscriber_queue)
        self._subscribers.add(queue)
        self._drops_by_subscriber[queue] = 0
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
        self._drops_by_subscriber.pop(queue, None)

    @property
    def subscribers(self) -> int:
        return len(self._subscribers)

    @property
    def queue_depth(self) -> int:
        return max((q.qsize() for q in self._subscribers), default=0)

    @property
    def history_size(self) -> int:
        return len(self._history)

    def history_since(self, sequence: int) -> list[Event]:
        """Eventos retenidos con ``sequence`` estrictamente mayor."""
        return [event for event in self._history if event.sequence > sequence]

    def _count_drop(self, queue: asyncio.Queue) -> None:
        self.events_dropped += 1
        self._drops_by_subscriber[queue] = self._drops_by_subscriber.get(queue, 0) + 1

    def publish(self, event: Event) -> bool:
        start = time.perf_counter()
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                    self._count_drop(queue)
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self._count_drop(queue)
        self.events_published += 1
        self._history.append(event)
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
            "dropped_subscribers": sum(1 for v in self._drops_by_subscriber.values() if v),
            "max_subscriber_drops": max(self._drops_by_subscriber.values(), default=0),
            "queue_depth": self.queue_depth,
            "history_size": self.history_size,
            "subscribers": self.subscribers,
            "publish_latency_p50_ms": p50,
            "publish_latency_p95_ms": p95,
        }

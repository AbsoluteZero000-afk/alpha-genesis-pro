from __future__ import annotations
import asyncio
from collections import deque
from typing import Deque, Optional
from .events import Event


class EventBus:
    """High-performance in-memory event bus with async support."""

    def __init__(self, max_size: int = 100_000) -> None:
        self._queue: Deque[Event] = deque(maxlen=max_size)
        self._event = asyncio.Event()

    def publish(self, event: Event) -> None:
        self._queue.append(event)
        self._event.set()

    async def next_event(self, timeout: Optional[float] = None) -> Optional[Event]:
        if self._queue:
            return self._queue.popleft()
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._event.clear()
        if self._queue:
            return self._queue.popleft()
        return None

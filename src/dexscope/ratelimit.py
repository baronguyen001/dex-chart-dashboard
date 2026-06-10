"""Process-wide request throttle.

A cold multi-timeframe page load (or ``dexscope warm``) can fire a dozen GeckoTerminal
calls back-to-back. :class:`RateLimiter` serializes them through a single lock so the
whole process stays under the free-tier rate limit, regardless of how many Flask worker
threads call it concurrently. The clock/sleep are injectable so tests run instantly.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

# Extra sleep (seconds) after each consecutive HTTP 429, indexed by retry attempt.
BACKOFFS: tuple[float, ...] = (6.0, 15.0, 30.0, 60.0)


class RateLimiter:
    def __init__(
        self,
        min_interval: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = max(0.0, float(min_interval))
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        """Block until at least ``min_interval`` has elapsed since the previous call."""
        with self._lock:
            elapsed = self._clock() - self._last
            remaining = self.min_interval - elapsed
            if remaining > 0:
                self._sleep(remaining)
            self._last = self._clock()

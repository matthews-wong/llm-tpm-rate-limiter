"""Continuously refilling token bucket."""

from __future__ import annotations

from typing import Callable

Clock = Callable[[], float]


class TokenBucket:
    """Holds up to `capacity` units and refills `capacity` units per `period` seconds.

    The level may go negative after `force_take`, which models a call whose
    real usage exceeded its estimate: later callers wait out the debt.
    """

    def __init__(self, capacity: float, clock: Clock, period: float = 60.0) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        if period <= 0:
            raise ValueError(f"period must be positive, got {period}")
        self.capacity = float(capacity)
        self._rate = capacity / period
        self._clock = clock
        self._level = float(capacity)
        self._updated = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._updated)
        self._level = min(self.capacity, self._level + elapsed * self._rate)
        self._updated = now

    @property
    def level(self) -> float:
        self._refill()
        return self._level

    def wait_time(self, amount: float) -> float:
        """Seconds until `amount` can be taken; 0 if available now."""
        if amount > self.capacity:
            raise ValueError(
                f"request of {amount} exceeds bucket capacity {self.capacity}; it can never be admitted"
            )
        self._refill()
        deficit = amount - self._level
        return max(0.0, deficit / self._rate)

    def force_take(self, amount: float) -> None:
        self._refill()
        self._level -= amount

    def refund(self, amount: float) -> None:
        self._refill()
        self._level = min(self.capacity, self._level + amount)

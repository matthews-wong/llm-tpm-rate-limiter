"""Two-axis limiter: requests per minute and tokens per minute."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from .bucket import Clock, TokenBucket


@dataclass(frozen=True)
class Reservation:
    tokens: int


class Limiter:
    def __init__(self, rpm: int, tpm: int, clock: Clock) -> None:
        self._requests = TokenBucket(rpm, clock)
        self._tokens = TokenBucket(tpm, clock)
        # Buckets are read-modify-write on a float; without this, two threads
        # can both see room for the same capacity and overspend the limit.
        self._lock = threading.Lock()

    def wait_time(self, estimated_tokens: int) -> float:
        """Seconds to wait before a call of this size fits both limits."""
        with self._lock:
            return self._wait_time(estimated_tokens)

    def _wait_time(self, estimated_tokens: int) -> float:
        return max(self._requests.wait_time(1), self._tokens.wait_time(estimated_tokens))

    def reserve(self, estimated_tokens: int) -> Reservation:
        """Charge both buckets unconditionally; prefer `try_reserve` across threads."""
        with self._lock:
            return self._reserve(estimated_tokens)

    def _reserve(self, estimated_tokens: int) -> Reservation:
        self._requests.force_take(1)
        self._tokens.force_take(estimated_tokens)
        return Reservation(tokens=estimated_tokens)

    def try_reserve(self, estimated_tokens: int) -> Reservation | float:
        """Check and charge in one step: a Reservation, or the seconds to wait."""
        with self._lock:
            wait = self._wait_time(estimated_tokens)
            if wait > 0:
                return wait
            return self._reserve(estimated_tokens)

    def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        """Reconcile the estimate with real usage: refund extra, charge a shortfall."""
        delta = reservation.tokens - actual_tokens
        with self._lock:
            if delta > 0:
                self._tokens.refund(delta)
            elif delta < 0:
                self._tokens.force_take(-delta)

    def release(self, reservation: Reservation) -> None:
        """Give back the token reservation for a call that never reached the model."""
        with self._lock:
            self._tokens.refund(reservation.tokens)

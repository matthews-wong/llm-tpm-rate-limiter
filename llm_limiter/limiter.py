"""Two-axis limiter: requests per minute and tokens per minute."""

from __future__ import annotations

from dataclasses import dataclass

from .bucket import Clock, TokenBucket


@dataclass(frozen=True)
class Reservation:
    tokens: int


class Limiter:
    def __init__(self, rpm: int, tpm: int, clock: Clock) -> None:
        self._requests = TokenBucket(rpm, clock)
        self._tokens = TokenBucket(tpm, clock)

    def wait_time(self, estimated_tokens: int) -> float:
        """Seconds to wait before a call of this size fits both limits."""
        return max(self._requests.wait_time(1), self._tokens.wait_time(estimated_tokens))

    def reserve(self, estimated_tokens: int) -> Reservation:
        """Charge both buckets. Call only after `wait_time` has elapsed."""
        self._requests.force_take(1)
        self._tokens.force_take(estimated_tokens)
        return Reservation(tokens=estimated_tokens)

    def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        """Reconcile the estimate with real usage: refund extra, charge a shortfall."""
        delta = reservation.tokens - actual_tokens
        if delta > 0:
            self._tokens.refund(delta)
        elif delta < 0:
            self._tokens.force_take(-delta)

    def release(self, reservation: Reservation) -> None:
        """Give back the token reservation for a call that never reached the model."""
        self._tokens.refund(reservation.tokens)

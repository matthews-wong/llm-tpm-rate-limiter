"""Rate-limited, retrying front for a provider."""

from __future__ import annotations

import random
import time
from typing import Callable

from .ledger import Ledger
from .limiter import Limiter, Reservation
from .provider import Provider, ProviderError, Request, Response
from .tokens import estimate_tokens

DEFAULT_MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_CAP_SECONDS = 30.0


class Gateway:
    def __init__(
        self,
        provider: Provider,
        limiter: Limiter,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        ledger: Ledger | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be at least 1, got {max_attempts}")
        self._provider = provider
        self._limiter = limiter
        self._max_attempts = max_attempts
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._ledger = ledger

    def complete(self, request: Request) -> Response:
        estimate = estimate_tokens(request.prompt, request.max_output_tokens)
        waited = 0.0
        for attempt in range(1, self._max_attempts + 1):
            reservation = self._limiter.try_reserve(estimate)
            while not isinstance(reservation, Reservation):
                self._sleep(reservation)
                waited += reservation
                reservation = self._limiter.try_reserve(estimate)
            try:
                response = self._provider.complete(request)
            except ProviderError as error:
                self._limiter.release(reservation)
                if not error.retryable or attempt == self._max_attempts:
                    raise
                delay = self._retry_delay(error, attempt)
                self._sleep(delay)
                waited += delay
                continue
            self._limiter.settle(reservation, response.tokens_used)
            if self._ledger is not None:
                self._ledger.record(estimate, response.tokens_used, attempt, waited)
            return response
        raise AssertionError("unreachable: the final attempt returns or raises")

    def _retry_delay(self, error: ProviderError, attempt: int) -> float:
        # The server's own hint beats our guess.
        if error.retry_after is not None:
            return error.retry_after
        ceiling = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * 2 ** (attempt - 1))
        return self._rng.uniform(0, ceiling)  # full jitter

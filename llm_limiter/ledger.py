"""Per-request record of what each call cost in tokens, money and waiting."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import List

TOKENS_PER_PRICE_UNIT = 1000


@dataclass(frozen=True)
class LedgerEntry:
    estimated_tokens: int
    actual_tokens: int
    attempts: int
    waited_seconds: float
    cost: float


class Ledger:
    """Thread-safe, append-only list of completed calls."""

    def __init__(self, price_per_1k_tokens: float = 0.0) -> None:
        if price_per_1k_tokens < 0:
            raise ValueError(f"price_per_1k_tokens must not be negative, got {price_per_1k_tokens}")
        self._price = price_per_1k_tokens
        self._lock = threading.Lock()
        self._entries: List[LedgerEntry] = []

    def record(self, estimated_tokens: int, actual_tokens: int, attempts: int, waited_seconds: float) -> LedgerEntry:
        entry = LedgerEntry(
            estimated_tokens,
            actual_tokens,
            attempts,
            waited_seconds,
            actual_tokens / TOKENS_PER_PRICE_UNIT * self._price,
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    @property
    def entries(self) -> List[LedgerEntry]:
        with self._lock:
            return list(self._entries)

    @property
    def total_tokens(self) -> int:
        return sum(entry.actual_tokens for entry in self.entries)

    @property
    def total_cost(self) -> float:
        return sum(entry.cost for entry in self.entries)

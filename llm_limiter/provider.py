"""Provider seam: every model call goes through `Provider.complete`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class Request:
    prompt: str
    max_output_tokens: int = 256


@dataclass(frozen=True)
class Response:
    text: str
    tokens_used: int


class ProviderError(Exception):
    """A failed call. `status` is the HTTP status, or None for network errors."""

    def __init__(self, message: str, status: Optional[int] = None, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after

    @property
    def retryable(self) -> bool:
        return self.status is None or self.status == 429 or self.status >= 500


class Provider(Protocol):
    def complete(self, request: Request) -> Response: ...

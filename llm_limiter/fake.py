"""Deterministic provider that replays a scripted sequence of outcomes."""

from __future__ import annotations

from typing import List, Union

from .provider import ProviderError, Request, Response

Outcome = Union[Response, ProviderError]


class FakeProvider:
    def __init__(self, outcomes: List[Outcome]) -> None:
        self._outcomes = list(outcomes)
        self.calls: List[Request] = []

    def complete(self, request: Request) -> Response:
        self.calls.append(request)
        if not self._outcomes:
            raise AssertionError(f"FakeProvider has no scripted outcome for call {len(self.calls)}")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome

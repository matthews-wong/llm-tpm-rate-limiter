"""Replay 20 calls through a tight limiter on a virtual clock and print the schedule.

Nothing here sleeps for real: the clock advances only when the gateway asks to wait.
"""

import random

from llm_limiter import Gateway, Limiter, Request, Response
from llm_limiter.fake import FakeProvider

RPM = 30
TPM = 4000
CALLS = 20
PROMPT_CHARS = 2400
MAX_OUTPUT = 200
ACTUAL_TOKENS = 450  # well under the ~800 estimate, so refunds matter


class VirtualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def main() -> None:
    clock = VirtualClock()
    provider = FakeProvider([Response("ok", ACTUAL_TOKENS) for _ in range(CALLS)])
    gateway = Gateway(provider, Limiter(RPM, TPM, clock), sleep=clock.sleep, rng=random.Random(0))
    for i in range(1, CALLS + 1):
        gateway.complete(Request("x" * PROMPT_CHARS, MAX_OUTPUT))
        print(f"call {i:2d} sent at t={clock.now:6.2f}s")
    print(f"{CALLS} calls (limits: {RPM} rpm, {TPM} tpm) finished in {clock.now:.1f} virtual seconds")


if __name__ == "__main__":
    main()

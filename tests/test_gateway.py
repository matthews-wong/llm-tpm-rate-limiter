import random
import unittest
from typing import List

from llm_limiter.fake import FakeProvider
from llm_limiter.gateway import Gateway
from llm_limiter.limiter import Limiter
from llm_limiter.provider import ProviderError, Request, Response
from tests.test_bucket import FakeClock


class GatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.slept: List[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.clock.now += seconds

    def gateway(self, outcomes, rpm=60, tpm=6000, **kwargs) -> Gateway:
        self.provider = FakeProvider(outcomes)
        return Gateway(
            self.provider,
            Limiter(rpm, tpm, self.clock),
            sleep=self.sleep,
            rng=random.Random(1),
            **kwargs,
        )

    def test_success_needs_no_sleep(self) -> None:
        response = self.gateway([Response("hi", 10)]).complete(Request("hello"))
        self.assertEqual(response.text, "hi")
        self.assertEqual(self.slept, [])

    def test_burst_waits_for_token_budget(self) -> None:
        gateway = self.gateway([Response("a", 4000), Response("b", 4000)])
        gateway.complete(Request("x" * 4 * 3900, max_output_tokens=100))
        gateway.complete(Request("x" * 4 * 3900, max_output_tokens=100))
        self.assertEqual(len(self.slept), 1)
        self.assertGreater(self.slept[0], 0)

    def test_retry_after_header_is_honoured(self) -> None:
        gateway = self.gateway([ProviderError("slow", 429, retry_after=7.0), Response("ok", 5)])
        self.assertEqual(gateway.complete(Request("p")).text, "ok")
        self.assertIn(7.0, self.slept)

    def test_backoff_is_jittered_and_capped(self) -> None:
        errors = [ProviderError("boom", 503)] * 4
        gateway = self.gateway(errors + [Response("ok", 5)], max_attempts=5)
        gateway.complete(Request("p"))
        for attempt, delay in enumerate(self.slept, start=1):
            self.assertLessEqual(delay, min(30.0, 2 ** (attempt - 1)))

    def test_client_error_is_not_retried(self) -> None:
        gateway = self.gateway([ProviderError("bad key", 401)])
        with self.assertRaisesRegex(ProviderError, "bad key"):
            gateway.complete(Request("p"))
        self.assertEqual(len(self.provider.calls), 1)

    def test_gives_up_after_max_attempts(self) -> None:
        gateway = self.gateway([ProviderError("down", 500)] * 3, max_attempts=3)
        with self.assertRaisesRegex(ProviderError, "down"):
            gateway.complete(Request("p"))
        self.assertEqual(len(self.provider.calls), 3)

    def test_failed_calls_return_their_token_reservation(self) -> None:
        gateway = self.gateway([ProviderError("x", 500), Response("ok", 10)])
        gateway.complete(Request("p", max_output_tokens=5000))
        # the retry fits the 6000 tpm budget without waiting for refill
        self.assertEqual(len(self.slept), 1)

    def test_rejects_zero_attempts(self) -> None:
        with self.assertRaisesRegex(ValueError, "got 0"):
            self.gateway([], max_attempts=0)


if __name__ == "__main__":
    unittest.main()

import random
import threading
import unittest

from llm_limiter.fake import FakeProvider
from llm_limiter.gateway import Gateway
from llm_limiter.ledger import Ledger
from llm_limiter.limiter import Limiter
from llm_limiter.provider import ProviderError, Request, Response
from tests.test_bucket import FakeClock


class LedgerTest(unittest.TestCase):
    def test_cost_is_actual_tokens_times_price(self) -> None:
        entry = Ledger(price_per_1k_tokens=0.5).record(100, 2000, 1, 0.0)
        self.assertAlmostEqual(entry.cost, 1.0)

    def test_negative_price_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "-1"):
            Ledger(price_per_1k_tokens=-1)

    def test_concurrent_records_are_all_kept(self) -> None:
        ledger = Ledger()
        threads = [threading.Thread(target=ledger.record, args=(1, 1, 1, 0.0)) for _ in range(50)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(ledger.entries), 50)


class GatewayLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.ledger = Ledger(price_per_1k_tokens=2.0)

    def sleep(self, seconds: float) -> None:
        self.clock.now += seconds

    def gateway(self, outcomes) -> Gateway:
        return Gateway(
            FakeProvider(outcomes),
            Limiter(60, 6000, self.clock),
            sleep=self.sleep,
            rng=random.Random(1),
            ledger=self.ledger,
        )

    def test_success_is_recorded_with_actual_usage(self) -> None:
        self.gateway([Response("a", 500)]).complete(Request("x" * 400, max_output_tokens=100))
        (entry,) = self.ledger.entries
        self.assertEqual((entry.estimated_tokens, entry.actual_tokens, entry.attempts), (200, 500, 1))
        self.assertAlmostEqual(entry.cost, 1.0)

    def test_retries_and_waiting_are_counted(self) -> None:
        gateway = self.gateway([ProviderError("slow down", 429, retry_after=3.0), Response("a", 10)])
        gateway.complete(Request("hi"))
        (entry,) = self.ledger.entries
        self.assertEqual(entry.attempts, 2)
        self.assertAlmostEqual(entry.waited_seconds, 3.0)

    def test_failed_call_is_not_billed(self) -> None:
        with self.assertRaises(ProviderError):
            self.gateway([ProviderError("bad request", 400)]).complete(Request("hi"))
        self.assertEqual(self.ledger.entries, [])

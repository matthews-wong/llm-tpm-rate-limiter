import unittest

from llm_limiter.limiter import Limiter
from tests.test_bucket import FakeClock


class LimiterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.limiter = Limiter(rpm=60, tpm=6000, clock=self.clock)

    def test_idle_limiter_admits_immediately(self) -> None:
        self.assertEqual(self.limiter.wait_time(1000), 0.0)

    def test_token_axis_can_be_the_bottleneck(self) -> None:
        self.limiter.reserve(6000)
        # 1000 tokens refill at 100/s
        self.assertAlmostEqual(self.limiter.wait_time(1000), 10.0)

    def test_request_axis_can_be_the_bottleneck(self) -> None:
        for _ in range(60):
            self.limiter.reserve(1)
        self.assertAlmostEqual(self.limiter.wait_time(1), 1.0)

    def test_settle_refunds_overestimate(self) -> None:
        reservation = self.limiter.reserve(5000)
        self.limiter.settle(reservation, 1000)
        self.assertEqual(self.limiter.wait_time(5000), 0.0)

    def test_settle_charges_underestimate(self) -> None:
        reservation = self.limiter.reserve(1000)
        self.limiter.settle(reservation, 6000)
        self.assertGreater(self.limiter.wait_time(1000), 0.0)

    def test_release_returns_tokens_but_not_the_request_slot(self) -> None:
        reservation = self.limiter.reserve(6000)
        self.limiter.release(reservation)
        self.assertEqual(self.limiter.wait_time(6000), 0.0)


if __name__ == "__main__":
    unittest.main()

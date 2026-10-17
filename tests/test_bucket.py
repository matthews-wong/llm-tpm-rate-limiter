import unittest

from llm_limiter.bucket import TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class TokenBucketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.bucket = TokenBucket(60, self.clock)  # 1 unit per second

    def test_starts_full(self) -> None:
        self.assertEqual(self.bucket.wait_time(60), 0.0)

    def test_wait_matches_deficit(self) -> None:
        self.bucket.force_take(60)
        self.assertAlmostEqual(self.bucket.wait_time(10), 10.0)

    def test_refills_over_time_up_to_capacity(self) -> None:
        self.bucket.force_take(30)
        self.clock.now = 1000
        self.assertEqual(self.bucket.level, 60)

    def test_debt_delays_next_caller(self) -> None:
        self.bucket.force_take(90)  # level -30
        self.assertAlmostEqual(self.bucket.wait_time(5), 35.0)

    def test_refund_is_capped(self) -> None:
        self.bucket.refund(500)
        self.assertEqual(self.bucket.level, 60)

    def test_oversized_request_is_rejected_with_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "61.*capacity 60"):
            self.bucket.wait_time(61)

    def test_rejects_non_positive_capacity(self) -> None:
        with self.assertRaisesRegex(ValueError, "-1"):
            TokenBucket(-1, self.clock)


if __name__ == "__main__":
    unittest.main()

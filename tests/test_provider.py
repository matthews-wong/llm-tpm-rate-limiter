import unittest

from llm_limiter.fake import FakeProvider
from llm_limiter.provider import ProviderError, Request, Response


class ProviderErrorTest(unittest.TestCase):
    def test_retryable_statuses(self) -> None:
        for status in (None, 429, 500, 503):
            self.assertTrue(ProviderError("x", status).retryable, status)

    def test_client_errors_are_not_retryable(self) -> None:
        for status in (400, 401, 404):
            self.assertFalse(ProviderError("x", status).retryable, status)


class FakeProviderTest(unittest.TestCase):
    def test_replays_outcomes_in_order(self) -> None:
        fake = FakeProvider([ProviderError("slow down", 429), Response("ok", 7)])
        with self.assertRaises(ProviderError):
            fake.complete(Request("a"))
        self.assertEqual(fake.complete(Request("b")).text, "ok")
        self.assertEqual([c.prompt for c in fake.calls], ["a", "b"])

    def test_running_out_of_script_fails_loudly(self) -> None:
        with self.assertRaisesRegex(AssertionError, "call 1"):
            FakeProvider([]).complete(Request("a"))


if __name__ == "__main__":
    unittest.main()

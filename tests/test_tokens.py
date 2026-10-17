import unittest

from llm_limiter.tokens import estimate_tokens


class EstimateTokensTest(unittest.TestCase):
    def test_rounds_prompt_up(self) -> None:
        self.assertEqual(estimate_tokens("abcde", 0), 2)

    def test_adds_output_cap(self) -> None:
        self.assertEqual(estimate_tokens("abcd", 100), 101)

    def test_empty_prompt(self) -> None:
        self.assertEqual(estimate_tokens("", 10), 10)


if __name__ == "__main__":
    unittest.main()

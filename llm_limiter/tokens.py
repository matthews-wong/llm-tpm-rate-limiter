"""Cheap token estimation, used only to reserve capacity before a call."""

# Rough average for English text; real usage replaces it after the call.
CHARS_PER_TOKEN = 4


def estimate_tokens(prompt: str, max_output_tokens: int) -> int:
    """Upper-bound-ish cost of a call: prompt tokens plus the output cap."""
    prompt_tokens = -(-len(prompt) // CHARS_PER_TOKEN)
    return prompt_tokens + max_output_tokens

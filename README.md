# llm-tpm-rate-limiter

Providers throttle LLM calls on two axes at once: requests per minute (RPM)
and tokens per minute (TPM). This is a small client-side limiter that
respects both, so a burst of calls waits locally instead of collecting 429s.

- Two token buckets (requests, tokens) that refill continuously.
- Reserve an *estimate* before the call, then reconcile with the real usage
  afterwards so over-estimates are refunded.
- Retries only on 429 / 5xx / network errors, honouring `Retry-After` and
  falling back to exponential backoff with jitter.
- Clock, sleep and RNG are injected, so everything is tested without waiting.
- Stdlib Python only. No API key needed; a deterministic fake provider ships
  in the repo.

## Usage

```python
from llm_limiter import Limiter, Gateway

gateway = Gateway(provider, Limiter(rpm=60, tpm=40_000))
response = gateway.complete(request)
```

## Validate

```
python3 -m unittest
```

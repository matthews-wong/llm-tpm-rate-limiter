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
import time
from llm_limiter import Limiter, Gateway

gateway = Gateway(provider, Limiter(rpm=60, tpm=40_000, clock=time.monotonic))
response = gateway.complete(request)
```

`provider` is anything with `complete(request) -> Response`; raise
`ProviderError(message, status, retry_after)` from it to opt into retries.

## Cost ledger

```python
from llm_limiter import Ledger

ledger = Ledger(price_per_1k_tokens=0.002)
gateway = Gateway(provider, limiter, ledger=ledger)
gateway.complete(request)
ledger.entries      # estimated/actual tokens, attempts, waited_seconds, cost
ledger.total_cost
```

Cost is priced on the provider's reported usage, not the estimate. Failed
calls are not recorded.

## Simulation

```
PYTHONPATH=. python3 examples/simulate.py
```

Runs 20 scripted calls (about 800 estimated tokens, 450 actual) through a
30 rpm / 4000 tpm limiter on a virtual clock. Output on that fixture: the
last call is sent at t=80.25s. Settling to actual usage is what keeps the
spacing near 6.75s instead of the ~12s the raw estimates would imply.

## Limits

- Token estimation is a 4-chars-per-token heuristic; real usage corrects it.
- A call larger than the whole TPM budget raises instead of waiting forever.
- One process only: the buckets are not shared across workers.

## Validate

```
python3 -m unittest
```

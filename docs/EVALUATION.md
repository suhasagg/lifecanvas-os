# Evaluation

Everything here was measured on this codebase. Nothing is estimated.

## Automated tests

`pytest -q`: **121 passed** (about 19 s, Python 3.12). `ruff check app tests scripts`: clean. All provider traffic in tests is served by an `httpx.MockTransport`, so the suite is offline and deterministic.

| File | Test functions | Covers |
| --- | --- | --- |
| `tests/test_security.py` | 11 | Password hashing, sentinel rules, redaction, URL and SSRF guards, audit-chain tamper detection, rate limiter |
| `tests/test_providers.py` | 12 | Catalog integrity, fail-closed configuration, retries and backoff, cache, no write retries, ambiguous outcomes, circuit breaker, host allowlist, status from real probes, model routing, fallback and cost accounting |
| `tests/test_memory.py` | 7 | Six layers, ranking, user isolation, preference learning, injection refusal, deletion |
| `tests/test_actions.py` | 15 | Validation, digest binding, tamper refusal, replay prevention, expiry, duplicates, unknown outcomes, dependencies, held actions, isolation, restart recovery, ledger |
| `tests/test_graph.py` | 19 | Compiled graph structure, subgraphs, `Send` fan-out, typed reducers, bounded revisions and loops, interrupt/resume, thread and user isolation, memory consolidation, tool allowlists, untrusted-content isolation, model-plan path, no sample-data code paths |
| `tests/test_budget_social.py` | 6 | Budget selection, flight-order spend cap, agent verdict privacy, meetup negotiation, video-call access |
| `tests/test_api.py` | 23 | Auth, CSRF, headers, cross-user access, SSE stream and cursor, approvals over HTTP, selective approval, community privacy, account deletion, limits, cancellation, restart recovery |

## Live verification

- The application was run against real providers and driven end to end in Chromium; `scripts/capture_screenshots.py` produced the 84 screenshots in [GALLERY.md](GALLERY.md) with no failed step.
- Credential-free providers returned live data during that run (Open-Meteo, OpenStreetMap Nominatim, iTunes, MusicBrainz, TheSportsDB, TVmaze, Open Library, Art Institute of Chicago, The Met, Wikipedia, Wikivoyage, DuckDuckGo).
- Overpass mirrors frequently timed out; the dining specialist fell back to Nominatim, as its trace shows.

## Not evaluated

- No language-model key was available, so there are no live measurements of model quality, token usage, cost or latency. The Developer view reports these from real calls once a model is connected.
- Credentialed read providers and all write connectors were not exercised against the real services.
- The budget planner, meetups and video-call screens were exercised once in Chromium with two accounts (screenshots 85-89); joining the Jitsi room itself was not tested.
- No load, concurrency or long-run soak testing was done.
- The Docker image and the CI workflow were written but not built or run.
- Answer relevance in rule-based mode was not scored; keyword routing can return loosely related results.

## Reproduce

```bash
pytest -q
ruff check app tests scripts
python scripts/capture_screenshots.py
```

# Architecture

## Layout

```
app/
  main.py            FastAPI app, auth, CSRF, security headers, routes
  runtime.py         run lifecycle: start, stream, interrupt/resume, cancel, recovery
  supervisor.py      hierarchical LangGraph supervisor
  subgraphs/         discovery (5 specialists), research, creative, action
  state.py           typed state, reducers, structured-output schemas
  agents/nlu.py      deterministic entity extraction
  tools/registry.py  read tools, per-agent allowlists, write-tool table
  providers/         gateway, catalog, registry (status), model router
  integrations/      provider adapters (read) and publish.py (write)
  memory.py          six-layer memory and local vector recall
  services/          approvals ledger, community, service container
  security.py        auth, sentinel, redaction, SSRF guard, audit chain
  repositories/db.py SQLite schema and access
web/                 Sunshine Edition client (ES modules, strict CSP)
tests/               offline test suite
```

## Supervisor graph

```
START → recall → sentinel ─┬─ blocked ─→ refuse ───────────────────────────────→ consolidate → END
                           └─ ok ─→ planner ─ Send per task ─→ [specialists] → critic
critic ─┬─ retry (≤ max_revisions) → redispatch ─ Send ─→ [specialists]
        └─ composer ─┬─ proposals → action (interrupt) → consolidate
                     └─ none → consolidate
```

| Node | Responsibility |
| --- | --- |
| recall | Ranked memory recall, preferences, recent turns |
| sentinel | Injection/abuse screening; blocked requests call no tool or model |
| planner | Structured `Plan` from a model when configured, else rules. Entity parameters always come from the deterministic extractor |
| specialists | Compiled subgraphs mounted as nodes, dispatched in parallel with `Send`, `RetryPolicy(max_attempts=2)` |
| critic | Independent validation: every card needs provider, link and retrieval time; coverage per task; transient failures trigger one bounded re-dispatch; optional second-opinion model from a different provider |
| composer | Answer from grounded results only; builds action proposals |
| action | Approval subgraph, suspended by `interrupt()` |
| consolidate | Writes conversation, working, episodic, semantic, procedural and preference memory |

State is a `TypedDict`; `results` uses a merge-by-task reducer so parallel branches and revisions combine safely, and `trace` uses a capped append reducer.

## Specialist subgraphs

- **Discovery (entertainment, dining, travel, community, culture):** `resolve → select → act → observe → (select | rank) → report`. `select` applies the agent's tool policy and skips unconfigured providers with a notice; `act` runs tools concurrently under a per-tool deadline; `observe` loops at most twice.
- **Research:** `plan_queries → Send(search)×N → extract → aggregate → synthesise → verify → (revise | report)`. `verify` keeps only claims found verbatim in retrieved source text and drops model sentences citing unknown sources.
- **Creative:** `research → ideate → outline → draft → adapt → critique → (revise | propose)`. It emits proposals only.
- **Action:** `prepare → gate → decide → execute → verify → (gate | END)`. The only graph that can reach write adapters.

## Runtime

- One LangGraph thread per run (`thread_id = run_id`) in `AsyncSqliteSaver`.
- Events are persisted to `run_events` and served over SSE with a resumable cursor.
- Approval: the run stops as `awaiting_approval`; `POST /api/actions/decide` resumes it with `Command(resume=...)`.
- Cancellation cancels the driving task; completed steps stay checkpointed.
- Restart: runs left `running` become `interrupted` and can be resumed from the last checkpoint; actions left `executing` become `unknown` and are never re-sent.
- Limits: 150 s per run, 14 s per tool, 3 concurrent runs per user.

## Memory

| Layer | Content |
| --- | --- |
| working | Scratchpad for the current thread |
| conversation | Threads and turns |
| episodic | What past runs asked and found |
| semantic | Verified claims with source URLs |
| procedural | Which workflow and specialists produced grounded results |
| preferences | Explicitly stated likes, diet, team, home city, budget |

Recall ranks by cosine similarity on a local hashed n-gram embedding, blended with recency and reinforcement. Secrets are redacted and instruction-like content is refused before storage. Every query is scoped by `user_id`.

## Model routing

`ModelRouter` builds a fallback chain of one model per configured provider, ordered by strategy (balanced, quality, cost, latency) with per-agent overrides. Failures and invalid structured output fall through to the next provider. Tokens come from provider usage fields; cost is tokens × list price. With no provider configured it raises `LLMUnavailable` and agents use their rule-based path, labelled as such in the UI.

## Request lifecycle

1. The browser posts a goal to `POST /api/runs`. The run row is created and the graph starts in the background; the call returns at once.
2. The browser opens `GET /api/runs/{id}/stream`. Every node writes an event row, and the stream relays rows in order, so a reconnect loses nothing.
3. `recall` loads relevant memory; `sentinel` screens the request. A blocked request ends here without calling a tool or a model.
4. `planner` turns the goal into tasks, one per specialist. Tasks are fanned out in parallel.
5. Each specialist runs its own bounded loop over read-only tools and returns normalised result cards with provider, link and retrieval time.
6. `critic` checks coverage and may send work back, up to `LIFECANVAS_MAX_REVISIONS` times.
7. `composer` writes the answer. If the plan contains external writes, the action graph proposes them and pauses with an interrupt.
8. After your decision the run resumes from its checkpoint, executes what you approved and records the outcome.
9. `consolidate` stores what is worth remembering.

## Approvals and the action graph

The action graph is the only place write adapters can be called: `prepare → gate → decide → execute → verify`. `gate` pauses the graph with a LangGraph interrupt; `decide` resumes it with your choice. Standalone approval batches from Creator Studio, My plans and the Action center run on their own thread, named `act-<batch id>`. See [Security](SECURITY.md) for the approval lifecycle.

## Budget, booking and social services

These are plain services called by the API, outside the agent graph, so that they stay deterministic and testable.

| Module | Role |
| --- | --- |
| `app/services/budget.py` | Chooses a combination of priced cards within a budget. See [Budget and booking](BOOKING.md). |
| `app/integrations/publish.py` (`amadeus_flight_order`) | Validates a flight order against the spending cap and sends it through the approval ledger. |
| `app/services/social.py` | Meetups, agent verdicts, confirmation and video-call rooms. See [Social agents](SOCIAL_AGENTS.md). |

## Data model

SQLite, one file for application data and one for checkpoints.

| Tables | Purpose |
| --- | --- |
| `users`, `sessions` | Accounts and hashed session tokens |
| `threads`, `messages` | Conversations |
| `memories` | Six memory layers per user |
| `runs`, `run_events` | Runs and their streamed events |
| `actions`, `ledger` | Proposed writes and every state transition |
| `profiles`, `connections`, `blocks`, `reports` | Community |
| `meetups`, `meetup_members` | Meetups and each participant's private limits |
| `plans` | Saved ideas |
| `provider_calls`, `provider_checks`, `llm_calls`, `tool_calls` | Telemetry |
| `audit`, `security_events` | Hash-chained audit log and safety events |

## Frontend

Vanilla JavaScript ES modules with no build step, served by the API under a strict Content Security Policy.

| File | Role |
| --- | --- |
| `web/index.html` | Page shell and navigation |
| `web/app.js` | Sign-in, routing and event handling |
| `web/js/core.js` | API client, escaping, result cards, drawers |
| `web/js/runs.js` | Run pipeline, stream handling, approval cards |
| `web/js/pages.js` | The 14 workspaces |
| `web/styles.css` | Sunshine Edition styles |

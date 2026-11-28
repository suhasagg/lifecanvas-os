# API

The interactive reference is served at `/api/docs`. This page explains the conventions and the main request and response shapes.

## Conventions

- Every route is under `/api` and returns JSON.
- Authentication is a session cookie set by `auth/register` or `auth/login`. It is HttpOnly and SameSite=Strict. There are no API keys for end users.
- Every state-changing request (`POST`, `PUT`, `DELETE`) must carry the header `X-Requested-With: lifecanvas` and a same-origin `Origin`.
- Every record is scoped to the signed-in user. Asking for another user's run, action, plan, memory or meetup returns "not found".
- Request bodies are limited to 200 KB.

### Errors

```json
{"error": "invalid_request", "message": "Budget must be greater than zero"}
```

| HTTP | `error` | Meaning |
| --- | --- | --- |
| 400 | `invalid_request` or `error` | Validation failed, or the request matched safety rules |
| 401 | `unauthenticated` | No valid session |
| 403 | `forbidden` | Missing CSRF header or foreign origin |
| 404 | `not_found` | Unknown record, or a record owned by someone else |
| 413 | `too_large` or `error` | Body or plan too large |
| 429 | `error` | Rate limit reached |

### Quick start with curl

```bash
H='X-Requested-With: lifecanvas'
curl -c jar -H "$H" -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"a-long-passphrase","name":"You"}' \
  http://localhost:8000/api/auth/register

curl -b jar -H "$H" -H 'Content-Type: application/json' \
  -d '{"goal":"Plan a jazz evening in Delhi with dinner","city":"Delhi","country":"IN"}' \
  http://localhost:8000/api/runs
# → {"run_id": "...", "thread_id": "...", "status": "running"}

curl -b jar -N http://localhost:8000/api/runs/<run_id>/stream
```

## Accounts

| Route | Body | Notes |
| --- | --- | --- |
| `POST auth/register` | `{email, password, name?}` | Creates the account and signs in. Rate limited per client. |
| `POST auth/login` | `{email, password}` | Rate limited per email. Failed attempts are recorded as security events. |
| `POST auth/logout` | none | Revokes the session server-side. |
| `GET me` | | The signed-in user. |
| `DELETE me` | | Erases the account, every user-scoped row and the saved graph checkpoints for the user's runs and approval batches. |

## Bootstrap

| Route | Notes |
| --- | --- |
| `GET health` | Liveness check; no session needed. |
| `GET bootstrap` | Everything the UI needs at start: the user, version, workflow presets, provider status counts, model routing, preferences, community profile, pending approval count, memory layers, platform length limits and action kinds. |
| `GET today?city=&country=` | Live Today dashboard: movie charts, fixtures, weather for the city, saved plans, pending approvals, recent runs and preferences. |

## Runs (the orchestrator)

A run is one execution of the supervisor graph. It is also one LangGraph thread, so it can be resumed after a restart.

| Route | Notes |
| --- | --- |
| `POST runs` | Start a run. Body below. Returns `{run_id, thread_id, status}` immediately. |
| `GET runs` | Recent runs. |
| `GET runs/{id}` | One run, with its answer once finished. |
| `GET runs/{id}/events?after=<seq>` | Events after a sequence number (polling alternative to the stream). |
| `GET runs/{id}/stream?after=<seq>` | Server-sent events. |
| `POST runs/{id}/cancel` | Request cancellation. |
| `POST runs/{id}/resume` | Resume an interrupted run from its last checkpoint. |
| `GET runs/{id}/checkpoints` | Checkpoint history for the developer view. |

`POST runs` body:

| Field | Type | Notes |
| --- | --- | --- |
| `goal` | string, 1-1200 | What you want, in plain language |
| `city`, `country` | string | City name and two-letter country code; optional |
| `workflow` | string | `auto`, `weekend`, `date_night`, `trip`, `matchday`, `wellness`, `social`, `research` or `create` |
| `strategy` | string | Model routing: `balanced`, `quality`, `cost` or `latency`; empty uses the server default |
| `thread_id` | string | Continue an existing conversation; ignored if it is not yours |

Run status is one of `running`, `awaiting_approval`, `completed`, `failed`, `cancelled` or `interrupted`.

### Stream events

Each SSE message has `id` (the sequence number), `event` and a JSON `data` body.

| Event | Meaning |
| --- | --- |
| `step` | A graph node finished: `node`, `summary`, `detail` |
| `interrupt` | The run is paused for your approval; carries the approval request |
| `status` | The run status changed |
| `final` | The composed answer |
| `end` | The stream is closing; `data.status` is the final status |

Reconnect with `?after=<last id>`. The server sends a comment line as a keep-alive while a run is quiet.

## Discovery and creation

`POST discover` runs one specialist directly, without the full supervisor.

```json
{"domain": "dining", "query": "vegetarian north indian", "city": "Delhi", "country": "IN", "filters": {"diets": ["vegetarian"]}}
```

`domain` is `entertainment`, `dining`, `travel`, `culture`, `community` or `research`. Recognised `filters` keys: `cuisines`, `diets`, `genres`, `sport`, `team`, `amenity`, `topic`, `origin`, `destination`, `interests`, `when`, `budget`, and the switches `wants_movies`, `wants_shows`, `wants_music`, `wants_events`, `wants_flights`, `wants_books`, `wants_art`, `wants_fitness`. The response is the specialist's result (cards, provider notes) plus a `trace` of the nodes that ran.

`POST create` runs the Creator Studio graph and returns drafts plus publication proposals. It never publishes.

| Field | Notes |
| --- | --- |
| `topic` | 2-200 characters |
| `notes` | Up to 2000 characters; secrets are redacted |
| `tone` | `warm`, `professional`, `playful` or `bold` |
| `platforms` | Up to six, default `["linkedin"]` |
| `to`, `channel`, `image_url` | Needed only for email, Slack and Instagram proposals |
| `skip_research` | Skip the research step |

### Result card

Every provider result is normalised to one shape:

`provider, provider_id, attribution, kind, title, url, summary, image, when, where, price, currency, availability, rating, tags, meta, retrieved_at`

`price`, `currency` and `availability` are present only when the provider supplied them. They are never estimated.

## Actions and approvals

Nothing is written to an outside service without an approval bound to the exact payload.

| Route | Body | Notes |
| --- | --- | --- |
| `GET actions` | | Your actions with status |
| `POST actions/propose` | `{items: [{kind, payload, summary, depends_on?}]}` (1-12 items) | `depends_on` lists indexes of earlier items in the same request. Validates each payload and creates pending actions. Returns `{batch_id, actions, rejected}`. Nothing is sent. |
| `POST actions/decide` | `{batch_id, approve: [{id, digest}], reject: [id]}` | The `digest` must match the payload you were shown. Approved actions execute. |
| `POST actions/{id}/execute` | | Execute an approved action that was held, for example after connecting the provider. |
| `GET actions/{id}/ledger` | | Every state transition of one action |

Action status: `pending` → `approved` → `executing` → `executed`, or `rejected`, `expired`, `failed` (nothing was sent) or `unknown` (the provider may have received it; it is never retried).

Action kinds and payloads:

| Kind | Payload |
| --- | --- |
| `x`, `linkedin`, `facebook`, `bluesky`, `mastodon`, `telegram`, `discord` | `{text}` |
| `instagram` | `{text, image_url}` (public HTTPS image) |
| `slack` | `{text, channel}` (explicit channel ID) |
| `wordpress` | `{title, text, status}` with `status` `draft` or `publish` |
| `gmail` | `{to, subject, text}` (one explicit recipient) |
| `google_calendar` | `{title, start, end, location?, description?}` |
| `google_tasks`, `todoist`, `ms_graph` | `{title, notes?}` |
| `google_drive` | `{title, text}` |
| `notion` | `{page_id, text}` |
| `spotify_playlist` | `{name, description?, tracks}` (up to 50 names) |
| `amadeus_flight_order` | `{offer, travelers, max_total, currency}`; see [Budget and booking](BOOKING.md) |

## Budget

`POST budget/plan`

```json
{"budget": 2500, "currency": "INR", "per_category": 1,
 "cards": [{"title": "Gig A", "kind": "event", "price": 1500, "currency": "INR", "score": 3}]}
```

Response: `{budget, currency, total, remaining, within_budget, selected, price_to_confirm, other_currency, note}`. Details in [Budget and booking](BOOKING.md).

## Community, meetups and video calls

| Route | Body | Notes |
| --- | --- | --- |
| `GET community/profile`, `PUT community/profile` | `{display_name, city, interests, bio, discoverable, adult_confirmed}` | Opt-in, city level only |
| `GET community/matches?interests=&city=` | | Discoverable members with shared interests |
| `GET community/connections` | | Incoming, outgoing, accepted and blocked |
| `POST community/requests` | `{user_id, message?}` | Send a connection request |
| `POST community/requests/{id}` | `{accept}` | Accept or decline |
| `POST community/block`, `POST community/unblock` | `{user_id}` | A block also closes shared meetups to both members |
| `POST community/report` | `{user_id, reason}` | |
| `POST community/call` | `{user_id}` | `{url, provider, note}`; only between connected, unblocked members |
| `GET meetups` | | Meetups you take part in |
| `POST meetups` | `{title, options, invitees, constraints}` | Invitees must be your connections |
| `POST meetups/{id}/constraints` | `{constraints}` | Give your agent your limits; triggers negotiation |
| `POST meetups/{id}/confirm` | | Confirm the agreed option for yourself |

Details in [Social agents](SOCIAL_AGENTS.md).

## Memory

| Route | Notes |
| --- | --- |
| `GET memory` | All six layers and the derived preferences |
| `GET memory/recall?q=` | What the assistant would recall for a query |
| `POST memory/preferences` | `{kind, value}`; `kind` is `cuisine`, `artist`, `team`, `diet`, `budget`, `travel_style`, `home_city` or `interest` |
| `DELETE memory/{id}` | Forget one item |
| `DELETE memory?layer=` | Clear one layer |
| `GET threads`, `GET threads/{id}` | Conversation history |

## Plans

| Route | Body |
| --- | --- |
| `GET plans` | |
| `POST plans` | `{kind, title, data, starts}`; `data` up to 60 KB |
| `DELETE plans/{id}` | |

Saved cards keep `price` and `currency` in `data` when the provider supplied them, which is what the budget planner reads.

## Providers

| Route | Notes |
| --- | --- |
| `GET providers` | Every provider with its status and the model routing table |
| `POST providers/{id}/verify` | Make one real probe call |
| `POST providers/verify-all` | Probe every configured provider |

Status is `connected_verified` only after a real probe succeeded. Keys that are present but unprobed report `configured_unverified`.

## Developer and safety

| Route | Notes |
| --- | --- |
| `GET dev/graph` | Supervisor and subgraph structure |
| `GET dev/tools` | Read tools and which agent may call each |
| `GET dev/telemetry` | Provider, tool and model call measurements |
| `GET security` | Audit-chain verification and recent security events |
| `POST security/screen` | Run the sentinel on a piece of text |

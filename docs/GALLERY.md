# LifeCanvasOS screenshot gallery

89 screenshots captured from the running application with Playwright and Chromium by `scripts/capture_screenshots.py`.
They show real provider responses retrieved at capture time and the real configuration-required states of providers without credentials. No language-model key was configured during capture, so planner, critic and composer ran in their rule-based mode, as labelled in the UI.

## Sign in

### 01. Sign in

Session-based sign in. Every workspace below is private to the signed-in account.

![Sign in](screenshots/01-sign-in.png)

### 02. Sign-in error

Failed sign-in returns a clear, non-revealing error.

![Sign-in error](screenshots/02-sign-in-error.png)

### 03. Create account

Account creation (PBKDF2-hashed password, HttpOnly SameSite=Strict session cookie).

![Create account](screenshots/03-create-account.png)

## Today

### 04. Today — first run

Before a city is set: live fixtures and movie charts load, weather asks for a city.

![Today — first run](screenshots/04-today-first-run.png)

### 05. Today — live dashboard

Live Open-Meteo forecast, TheSportsDB fixtures and the iTunes movie chart for the selected city.

![Today — live dashboard](screenshots/05-today-live.png)

### 06. Today — full page

The complete Today workspace in the Sunshine Edition layout.

![Today — full page](screenshots/06-today-full.png)

### 07. How it works

In-app explainer: live sources, honest states, memory control, approvals, handoffs.

![How it works](screenshots/07-how-it-works.png)

## AI concierge

### 08. AI concierge

Conversation on the left; the live agent pipeline and step stream on the right.

![AI concierge](screenshots/08-concierge-empty.png)

### 09. Concierge — streaming run

Server-sent events stream each graph step (recall, sentinel, planner, parallel specialists) as it happens.

![Concierge — streaming run](screenshots/09-concierge-streaming.png)

### 10. Concierge — answer and trace

Finished run: composed answer, completed pipeline and the full tool trace with latencies.

![Concierge — answer and trace](screenshots/10-concierge-answer.png)

### 11. Concierge — grounded results

Result sections per specialist with provider attribution, configuration-required notices and app handoffs.

![Concierge — grounded results](screenshots/11-concierge-results.png)

### 12. Result detail

Detail drawer: metadata, provenance, retrieval time and source link for one result.

![Result detail](screenshots/12-concierge-card-detail.png)

### 13. Concierge — sentinel block

A prompt-injection attempt is refused by the sentinel before any tool or model is called.

![Concierge — sentinel block](screenshots/13-concierge-blocked.png)

### 14. Concierge — weather and sights

Follow-up in the same thread: the travel specialist returns the live forecast, a guide and landmarks.

![Concierge — weather and sights](screenshots/14-concierge-travel.png)

## Experiences

### 15. Experiences — live events

Event search. Ticketmaster shows its real configuration-required state; MusicBrainz event records are live.

![Experiences — live events](screenshots/15-experiences-events.png)

### 16. Experiences — sport

Upcoming fixtures from TheSportsDB with badges, venues and kick-off times.

![Experiences — sport](screenshots/16-experiences-sport.png)

### 17. Experiences — movies

Current iTunes movie chart with real prices and currency; TMDB shows configuration required.

![Experiences — movies](screenshots/17-experiences-movies.png)

### 18. Experiences — TV shows

TVmaze show search with ratings, networks and status.

![Experiences — TV shows](screenshots/18-experiences-shows.png)

### 19. Experiences — music

Track search with artwork, price and audio previews from the iTunes Search API.

![Experiences — music](screenshots/19-experiences-music.png)

### 20. Experiences — artists

Artist identity and genre tags from MusicBrainz and iTunes.

![Experiences — artists](screenshots/20-experiences-artists.png)

### 21. Track detail with preview

Drawer with artwork, price, duration and a playable preview supplied by the provider.

![Track detail with preview](screenshots/21-experiences-track-detail.png)

### 22. Experiences — team search

Team lookup plus that team's next fixtures.

![Experiences — team search](screenshots/22-experiences-team.png)

## Food & dining

### 23. Food & dining — restaurants

OpenStreetMap restaurants near the city centre. Google Places and Foursquare show configuration required.

![Food & dining — restaurants](screenshots/23-dining-restaurants.png)

### 24. Food & dining — cuisine and diet filter

Cuisine and dietary filters; results explain why they ranked and flag when a diet is not stated by the source.

![Food & dining — cuisine and diet filter](screenshots/24-dining-filtered.png)

### 25. Place detail

Opening hours, cuisine, dietary tags, map link and OpenStreetMap attribution.

![Place detail](screenshots/25-dining-place-detail.png)

### 26. Food & dining — how this was found

The dining specialist's ReAct steps (resolve, select, act, observe, rank, report) for this search.

![Food & dining — how this was found](screenshots/26-dining-trace.png)

### 27. Food & dining — cafes

Cafe search with booking and delivery app handoffs below the results.

![Food & dining — cafes](screenshots/27-dining-cafes.png)

## Circles

### 28. Circles — opt-in profile

Nothing is discoverable until you confirm you are an adult and opt in. No sample profiles exist.

![Circles — opt-in profile](screenshots/28-circles-profile.png)

### 29. Circles — interest matches

A real opted-in member matched by shared interests and city. Exact location and contact details are never shown.

![Circles — interest matches](screenshots/29-circles-matches.png)

### 30. Circles — request sent

Connection request recorded; block and report are available on every member.

![Circles — request sent](screenshots/30-circles-request-sent.png)

### 31. Circles — incoming request (second account)

The other member's view: accept, decline, block or report.

![Circles — incoming request (second account)](screenshots/31-circles-incoming.png)

### 32. Circles — connected

After acceptance both members see the connection.

![Circles — connected](screenshots/32-circles-connected.png)

## Creator studio

### 33. Creator studio

Choose platforms, give a topic and optional notes. A draft never posts by itself.

![Creator studio](screenshots/33-studio-empty.png)

### 34. Creator studio — brief

Multi-platform selection with tone control and the author's own notes.

![Creator studio — brief](screenshots/34-studio-brief.png)

### 35. Creator studio — platform variants

One researched draft adapted to each platform's limit; every variant stays editable.

![Creator studio — platform variants](screenshots/35-studio-drafts.png)

### 36. Creator studio — drafts and evidence

Variants, character counts and the cited research evidence used for the draft.

![Creator studio — drafts and evidence](screenshots/36-studio-full.png)

### 37. Creator studio — angles, outline and trace

The creative subgraph's research, ideate, outline, draft, adapt, critique and propose steps.

![Creator studio — angles, outline and trace](screenshots/37-studio-outline.png)

### 38. Creator studio — approval request

Publishing creates approval requests with destination, visibility, risk, expiry and payload digest.

![Creator studio — approval request](screenshots/38-studio-approval.png)

## Orchestrator

### 39. Orchestrator

Workflow presets, model-routing strategy and the live pipeline.

![Orchestrator](screenshots/39-orchestrator.png)

### 40. Orchestrator — parallel specialists running

Three specialist subgraphs fan out in parallel; steps stream as they complete.

![Orchestrator — parallel specialists running](screenshots/40-orchestrator-running.png)

### 41. Orchestrator — completed pipeline

All eight stages complete, with the per-tool trace.

![Orchestrator — completed pipeline](screenshots/41-orchestrator-trace.png)

### 42. Orchestrator — run result

KPIs, the composed answer, how planner/critic/composer ran, and grounded sections.

![Orchestrator — run result](screenshots/42-orchestrator-result.png)

### 43. Persistent checkpoints

The run's saved LangGraph checkpoints in SQLite; runs resume from the newest one.

![Persistent checkpoints](screenshots/43-orchestrator-checkpoints.png)

### 44. Deep research with verified citations

Parallel search, extraction and citation verification: every claim is traced to retrieved source text.

![Deep research with verified citations](screenshots/44-orchestrator-research.png)

### 45. Trip builder

Travel, dining and culture specialists combined for a destination.

![Trip builder](screenshots/45-orchestrator-trip.png)

### 46. Human-approval interrupt

The graph is suspended at the approval gate (LangGraph interrupt). Nothing has been sent.

![Human-approval interrupt](screenshots/46-orchestrator-interrupt.png)

### 47. Run history

Persisted runs with status; interrupted runs can be resumed from their checkpoint.

![Run history](screenshots/47-orchestrator-history.png)

## Culture & wellness

### 48. Culture — books

Open Library search with covers and ratings; Google Books shows configuration required.

![Culture — books](screenshots/48-culture-books.png)

### 49. Culture — art and museums

Artworks from the Art Institute of Chicago and The Met open-access collections.

![Culture — art and museums](screenshots/49-culture-art.png)

### 50. Artwork detail

Museum, medium, date and public-domain status with the collection link.

![Artwork detail](screenshots/50-culture-art-detail.png)

### 51. Culture — movement

Strava requires the owner's token: the real configuration-required state plus live conditions for getting outside.

![Culture — movement](screenshots/51-culture-movement.png)

## Travel & escapes

### 52. Travel & escapes

Destination presets and the trip form.

![Travel & escapes](screenshots/52-travel.png)

### 53. Travel — forecast and flights state

Live forecast for the destination; Amadeus flight offers show configuration required rather than invented fares.

![Travel — forecast and flights state](screenshots/53-travel-results.png)

### 54. Travel — guide, sights and handoffs

Wikivoyage guide, nearby landmarks with images, and booking-app handoffs.

![Travel — guide, sights and handoffs](screenshots/54-travel-full.png)

## My plans

### 55. My plans

Saved results and personal ideas, stored per account on the server.

![My plans](screenshots/55-plans.png)

### 56. Calendar event approval

A calendar entry becomes an approval request with exact start, end and timezone offset.

![Calendar event approval](screenshots/56-plans-calendar-approval.png)

## Action center

### 57. Action center — pending approvals

All pending approvals in one place: platform, destination, visibility, time, cost, dependencies, risk and digest.

![Action center — pending approvals](screenshots/57-actions-pending.png)

### 58. Action center — full view

Approval batches, the batch builder and history.

![Action center — full view](screenshots/58-actions-full.png)

### 59. Execution ledger

Per-action ledger of state transitions, with the exact payload and its SHA-256 digest.

![Execution ledger](screenshots/59-actions-ledger.png)

### 60. Approved and held

Approved actions for unconnected providers are held: nothing is sent and the missing credential is named.

![Approved and held](screenshots/60-actions-approved-held.png)

### 61. Action builder and history

Build a multi-app batch by hand; decided actions and receipts are kept in history.

![Action builder and history](screenshots/61-actions-builder.png)

### 62. Payload validation

Invalid payloads are refused before they can be proposed.

![Payload validation](screenshots/62-actions-validation.png)

## Memory & safety

### 63. Six memory layers

Working, conversation, episodic, semantic, procedural and preference memory, each inspectable and deletable.

![Six memory layers](screenshots/63-memory-layers.png)

### 64. Semantic recall test

Ranked recall from the local embedding index with similarity scores.

![Semantic recall test](screenshots/64-memory-recall.png)

### 65. Memory & safety — full page

All layers, security controls, security events and the hash-chained audit log.

![Memory & safety — full page](screenshots/65-memory-full.png)

### 66. Security controls and audit chain

Active controls, the blocked injection event and audit-chain verification status.

![Security controls and audit chain](screenshots/66-security-controls.png)

### 67. Sentinel and redaction

Try the sentinel: matched rules are listed and secrets/PII are redacted.

![Sentinel and redaction](screenshots/67-security-sentinel.png)

## Developer view

### 68. Compiled graph topology

The supervisor and eight specialist subgraphs read from the compiled LangGraph object.

![Compiled graph topology](screenshots/68-developer-graph.png)

### 69. Developer view — full page

Tool allowlists, model routing and measured telemetry from this installation.

![Developer view — full page](screenshots/69-developer-full.png)

### 70. Mermaid source

Mermaid export of the compiled graph, including subgraph nodes and conditional edges.

![Mermaid source](screenshots/70-developer-mermaid.png)

### 71. Measured telemetry

Tool, provider and model usage measured from real calls. Model rows stay empty until a model is connected.

![Measured telemetry](screenshots/71-developer-telemetry.png)

## App connections

### 72. Provider registry

Every provider with its real status: connected and verified, ready, configuration required or external handoff.

![Provider registry](screenshots/72-connections.png)

### 73. Live verification

After live probe calls: providers are only marked connected when a real request succeeded.

![Live verification](screenshots/73-connections-verified.png)

### 74. Configuration required

Credentialed providers list the exact environment variables they need.

![Configuration required](screenshots/74-connections-needs-setup.png)

### 75. Publishing connectors

Write connectors with required scopes; all require approval.

![Publishing connectors](screenshots/75-connections-social.png)

### 76. Provider detail

Capabilities, limits, retry policy, cache, usage and attribution for one provider.

![Provider detail](screenshots/76-connections-detail.png)

### 77. Dining providers and handoffs

API providers alongside honest app handoffs (Zomato, Swiggy, OpenTable, Google Maps).

![Dining providers and handoffs](screenshots/77-connections-dining.png)

## Responsive

### 78. Mobile — Today

The Sunshine layout at 390 px.

![Mobile — Today](screenshots/78-mobile-today.png)

### 79. Mobile — Food & dining

Responsive layout on a phone-sized viewport.

![Mobile — Food & dining](screenshots/79-mobile-dining.png)

### 80. Mobile — Action center

Responsive layout on a phone-sized viewport.

![Mobile — Action center](screenshots/80-mobile-actions.png)

### 81. Mobile — App connections

Responsive layout on a phone-sized viewport.

![Mobile — App connections](screenshots/81-mobile-connections.png)

### 82. Mobile — AI concierge

Responsive layout on a phone-sized viewport.

![Mobile — AI concierge](screenshots/82-mobile-concierge.png)

### 83. Tablet — Orchestrator

Layout at 900 px.

![Tablet — Orchestrator](screenshots/83-tablet-orchestrator.png)

## Sign in

### 84. Signed out

Signing out revokes the server-side session.

![Signed out](screenshots/84-signed-out.png)

## Social agents, video calls and budget

### 85. Video call

A private video room for two connected members.

![Video call](screenshots/85-circles-video-call.png)

### 86. Plan together

Start a meetup with options and your private limits.

![Plan together](screenshots/86-meetup-created.png)

### 87. Agents agreed

The other member's view after sharing limits: the agents picked the option that fits everyone.

![Agents agreed](screenshots/87-meetup-agents-agreed.png)

### 88. Meetup confirmed

Everyone confirmed; a group video call is available.

![Meetup confirmed](screenshots/88-meetup-confirmed.png)

### 89. Budget planner

Best combination of saved ideas within a budget, from provider-supplied prices.

![Budget planner](screenshots/89-budget-planner.png)


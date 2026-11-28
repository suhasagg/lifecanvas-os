<h1 align="center">LifeCanvasOS</h1>
<p align="center"><b>Every day is an adventure.</b><br>Your personal AI operating system for experiences, food, travel, culture, community, publishing and getting things done.</p>

<p align="center"><img src="docs/screenshots/05-today-live.png" alt="LifeCanvasOS Today" width="100%"></p>

LifeCanvasOS finds things worth doing, plans them around your tastes and budget, and carries them out across your apps, with your approval at every step that leaves the product.

## Contents

- [Why LifeCanvasOS](#why-lifecanvasos)
- [Product tour](#product-tour)
- [Budget and booking](#budget-and-booking)
- [Social agents and video calls](#social-agents-and-video-calls)
- [Agent architecture](#agent-architecture)
- [Get started](#get-started)
- [Connect your apps](#connect-your-apps)
- [Security and privacy](#security-and-privacy)
- [Quality](#quality)
- [Current limits](#current-limits)
- [Documentation](#documentation)

## Why LifeCanvasOS

| | |
| --- | --- |
| **Live answers** | Results come from real providers, each with attribution, a source link and the time it was retrieved. |
| **Honest states** | A provider that is not connected says so. Prices and availability appear only when the provider supplies them. |
| **One request, many specialists** | Entertainment, dining, travel, culture, community, research and writing agents work in parallel. |
| **Plans that fit your budget** | Tell it what you can spend; it picks the best combination that stays under the limit. |
| **You stay in control** | Nothing is posted, sent, booked or paid for without your approval of the exact details. |
| **Agents that plan together** | Members' agents negotiate a meetup that fits everyone, sharing verdicts instead of private budgets or calendars. |
| **Memory you own** | It learns stated preferences and shows you everything it remembers. Delete any of it. |

## 🎬 Product Demo

[![LifeCanvasOS Product Demo](docs/screenshots/05-today-live.png)](https://www.loom.com/share/4ccc82bae7a24fa6863eb95d72c5c80d)

### [▶ Watch the Full 10-Minute Product Walkthrough on Loom](https://www.loom.com/share/4ccc82bae7a24fa6863eb95d72c5c80d)

### Features Demonstrated

- **AI Concierge** — Conversational queries, personalized discovery and source-grounded recommendations.
- **Experiences** — Concerts, sports, movies, music and entertainment discovery.
- **Food & Dining** — Restaurant discovery, cuisine filters and dietary preferences.
- **Social Agents** — Interest matching, agent-to-agent negotiation and collaborative meetup planning.
- **Video Rooms** — Private and group video calls.
- **Creator Studio** — Automated research, content generation and multi-platform publishing workflows.
- **Budget Planner** — Intelligent activity optimization within spending constraints.
- **Travel & Escapes** — Destination discovery and personalized trip planning.
- **Multi-Agent Orchestrator** — Hierarchical supervision, parallel specialist execution, streaming and persistent checkpoints.
- **Action Center** — Human-in-the-loop approvals, secure execution and auditing.
- **Memory & Safety** — Six memory layers, semantic retrieval, personalization and AI security.
- **Developer Console** — Agent topology, intelligent model routing and execution observability.
- **App Connections** — External API integrations and application handoffs.
- **Responsive Experience** — Desktop, tablet and mobile interfaces.
LifeCanvasOS — Your Life. Connected by AI.


## Product tour

### Today

Your day at a glance: the live forecast for your city, upcoming fixtures, the current movie chart, approvals waiting for you and your recent activity.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/05-today-live.png" alt="Today — live dashboard"><br><b>Today — live dashboard</b><br><sub>Live Open-Meteo forecast, TheSportsDB fixtures and the iTunes movie chart for the selected city.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/06-today-full.png" alt="Today — full page"><br><b>Today — full page</b><br><sub>The complete Today workspace in the Sunshine Edition layout.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/04-today-first-run.png" alt="Today — first run"><br><b>Today — first run</b><br><sub>Before a city is set: live fixtures and movie charts load, weather asks for a city.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/07-how-it-works.png" alt="How it works"><br><b>How it works</b><br><sub>In-app explainer: live sources, honest states, memory control, approvals, handoffs.</sub></td></tr>
</table>

### AI concierge

Ask in plain language. A supervisor plans the work, specialist agents search live sources in parallel and every step streams to you as it happens. Results name their source and when they were retrieved.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/08-concierge-empty.png" alt="AI concierge"><br><b>AI concierge</b><br><sub>Conversation on the left; the live agent pipeline and step stream on the right.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/09-concierge-streaming.png" alt="Concierge — streaming run"><br><b>Concierge — streaming run</b><br><sub>Server-sent events stream each graph step (recall, sentinel, planner, parallel specialists) as it happens.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/10-concierge-answer.png" alt="Concierge — answer and trace"><br><b>Concierge — answer and trace</b><br><sub>Finished run: composed answer, completed pipeline and the full tool trace with latencies.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/11-concierge-results.png" alt="Concierge — grounded results"><br><b>Concierge — grounded results</b><br><sub>Result sections per specialist with provider attribution, configuration-required notices and app handoffs.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/12-concierge-card-detail.png" alt="Result detail"><br><b>Result detail</b><br><sub>Detail drawer: metadata, provenance, retrieval time and source link for one result.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/14-concierge-travel.png" alt="Concierge — weather and sights"><br><b>Concierge — weather and sights</b><br><sub>Follow-up in the same thread: the travel specialist returns the live forecast, a guide and landmarks.</sub></td></tr>
</table>

### Experiences

Concerts and festivals, sport fixtures, movies, TV, music with previews, and artists.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/15-experiences-events.png" alt="Experiences — live events"><br><b>Experiences — live events</b><br><sub>Event search. Ticketmaster shows its real configuration-required state; MusicBrainz event records are live.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/16-experiences-sport.png" alt="Experiences — sport"><br><b>Experiences — sport</b><br><sub>Upcoming fixtures from TheSportsDB with badges, venues and kick-off times.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/17-experiences-movies.png" alt="Experiences — movies"><br><b>Experiences — movies</b><br><sub>Current iTunes movie chart with real prices and currency; TMDB shows configuration required.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/18-experiences-shows.png" alt="Experiences — TV shows"><br><b>Experiences — TV shows</b><br><sub>TVmaze show search with ratings, networks and status.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/19-experiences-music.png" alt="Experiences — music"><br><b>Experiences — music</b><br><sub>Track search with artwork, price and audio previews from the iTunes Search API.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/20-experiences-artists.png" alt="Experiences — artists"><br><b>Experiences — artists</b><br><sub>Artist identity and genre tags from MusicBrainz and iTunes.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/21-experiences-track-detail.png" alt="Track detail with preview"><br><b>Track detail with preview</b><br><sub>Drawer with artwork, price, duration and a playable preview supplied by the provider.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/22-experiences-team.png" alt="Experiences — team search"><br><b>Experiences — team search</b><br><sub>Team lookup plus that team's next fixtures.</sub></td></tr>
</table>

### Food & dining

Restaurants, cafes and bars near you with cuisine and dietary filters, opening hours, map links and one-tap handoffs to booking and delivery apps.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/23-dining-restaurants.png" alt="Food & dining — restaurants"><br><b>Food & dining — restaurants</b><br><sub>OpenStreetMap restaurants near the city centre. Google Places and Foursquare show configuration required.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/24-dining-filtered.png" alt="Food & dining — cuisine and diet filter"><br><b>Food & dining — cuisine and diet filter</b><br><sub>Cuisine and dietary filters; results explain why they ranked and flag when a diet is not stated by the source.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/25-dining-place-detail.png" alt="Place detail"><br><b>Place detail</b><br><sub>Opening hours, cuisine, dietary tags, map link and OpenStreetMap attribution.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/26-dining-trace.png" alt="Food & dining — how this was found"><br><b>Food & dining — how this was found</b><br><sub>The dining specialist's ReAct steps (resolve, select, act, observe, rank, report) for this search.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/27-dining-cafes.png" alt="Food & dining — cafes"><br><b>Food & dining — cafes</b><br><sub>Cafe search with booking and delivery app handoffs below the results.</sub></td></tr>
</table>

### Travel & escapes

Destination forecast, guide and sights, flight offers when Amadeus is connected, and booking-app handoffs.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/52-travel.png" alt="Travel & escapes"><br><b>Travel & escapes</b><br><sub>Destination presets and the trip form.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/53-travel-results.png" alt="Travel — forecast and flights state"><br><b>Travel — forecast and flights state</b><br><sub>Live forecast for the destination; Amadeus flight offers show configuration required rather than invented fares.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/54-travel-full.png" alt="Travel — guide, sights and handoffs"><br><b>Travel — guide, sights and handoffs</b><br><sub>Wikivoyage guide, nearby landmarks with images, and booking-app handoffs.</sub></td></tr>
</table>

### Budget & booking

Set a budget and LifeCanvasOS builds the best plan that fits it from real, provider-supplied prices, then takes you to checkout. See [Budget and booking](#budget-and-booking) below.


### Culture & wellness

Books, open-access museum collections and your own activity.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/48-culture-books.png" alt="Culture — books"><br><b>Culture — books</b><br><sub>Open Library search with covers and ratings; Google Books shows configuration required.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/49-culture-art.png" alt="Culture — art and museums"><br><b>Culture — art and museums</b><br><sub>Artworks from the Art Institute of Chicago and The Met open-access collections.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/50-culture-art-detail.png" alt="Artwork detail"><br><b>Artwork detail</b><br><sub>Museum, medium, date and public-domain status with the collection link.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/51-culture-movement.png" alt="Culture — movement"><br><b>Culture — movement</b><br><sub>Strava requires the owner's token: the real configuration-required state plus live conditions for getting outside.</sub></td></tr>
</table>

### Circles

Meet people through shared interests at city level. Strictly opt-in, with requests, block and report.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/28-circles-profile.png" alt="Circles — opt-in profile"><br><b>Circles — opt-in profile</b><br><sub>Nothing is discoverable until you confirm you are an adult and opt in. No sample profiles exist.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/29-circles-matches.png" alt="Circles — interest matches"><br><b>Circles — interest matches</b><br><sub>A real opted-in member matched by shared interests and city. Exact location and contact details are never shown.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/30-circles-request-sent.png" alt="Circles — request sent"><br><b>Circles — request sent</b><br><sub>Connection request recorded; block and report are available on every member.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/31-circles-incoming.png" alt="Circles — incoming request (second account)"><br><b>Circles — incoming request (second account)</b><br><sub>The other member's view: accept, decline, block or report.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/32-circles-connected.png" alt="Circles — connected"><br><b>Circles — connected</b><br><sub>After acceptance both members see the connection.</sub></td></tr>
</table>

### Creator studio

Research a topic, draft once, adapt for each platform, review, then send for approval.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/33-studio-empty.png" alt="Creator studio"><br><b>Creator studio</b><br><sub>Choose platforms, give a topic and optional notes. A draft never posts by itself.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/34-studio-brief.png" alt="Creator studio — brief"><br><b>Creator studio — brief</b><br><sub>Multi-platform selection with tone control and the author's own notes.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/35-studio-drafts.png" alt="Creator studio — platform variants"><br><b>Creator studio — platform variants</b><br><sub>One researched draft adapted to each platform's limit; every variant stays editable.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/36-studio-full.png" alt="Creator studio — drafts and evidence"><br><b>Creator studio — drafts and evidence</b><br><sub>Variants, character counts and the cited research evidence used for the draft.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/37-studio-outline.png" alt="Creator studio — angles, outline and trace"><br><b>Creator studio — angles, outline and trace</b><br><sub>The creative subgraph's research, ideate, outline, draft, adapt, critique and propose steps.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/38-studio-approval.png" alt="Creator studio — approval request"><br><b>Creator studio — approval request</b><br><sub>Publishing creates approval requests with destination, visibility, risk, expiry and payload digest.</sub></td></tr>
</table>

### My plans

Save anything you find and turn it into calendar entries and tasks.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/55-plans.png" alt="My plans"><br><b>My plans</b><br><sub>Saved results and personal ideas, stored per account on the server.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/56-plans-calendar-approval.png" alt="Calendar event approval"><br><b>Calendar event approval</b><br><sub>A calendar entry becomes an approval request with exact start, end and timezone offset.</sub></td></tr>
</table>

### Orchestrator

Workflow presets for weekends, trips, match days, research and publishing, with live progress, checkpoints and resume.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/39-orchestrator.png" alt="Orchestrator"><br><b>Orchestrator</b><br><sub>Workflow presets, model-routing strategy and the live pipeline.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/40-orchestrator-running.png" alt="Orchestrator — parallel specialists running"><br><b>Orchestrator — parallel specialists running</b><br><sub>Three specialist subgraphs fan out in parallel; steps stream as they complete.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/41-orchestrator-trace.png" alt="Orchestrator — completed pipeline"><br><b>Orchestrator — completed pipeline</b><br><sub>All eight stages complete, with the per-tool trace.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/42-orchestrator-result.png" alt="Orchestrator — run result"><br><b>Orchestrator — run result</b><br><sub>KPIs, the composed answer, how planner/critic/composer ran, and grounded sections.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/43-orchestrator-checkpoints.png" alt="Persistent checkpoints"><br><b>Persistent checkpoints</b><br><sub>The run's saved LangGraph checkpoints in SQLite; runs resume from the newest one.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/44-orchestrator-research.png" alt="Deep research with verified citations"><br><b>Deep research with verified citations</b><br><sub>Parallel search, extraction and citation verification: every claim is traced to retrieved source text.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/45-orchestrator-trip.png" alt="Trip builder"><br><b>Trip builder</b><br><sub>Travel, dining and culture specialists combined for a destination.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/46-orchestrator-interrupt.png" alt="Human-approval interrupt"><br><b>Human-approval interrupt</b><br><sub>The graph is suspended at the approval gate (LangGraph interrupt). Nothing has been sent.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/47-orchestrator-history.png" alt="Run history"><br><b>Run history</b><br><sub>Persisted runs with status; interrupted runs can be resumed from their checkpoint.</sub></td></tr>
</table>

### Action center

Every post, email, calendar entry, task and booking waits here until you approve the exact content.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/57-actions-pending.png" alt="Action center — pending approvals"><br><b>Action center — pending approvals</b><br><sub>All pending approvals in one place: platform, destination, visibility, time, cost, dependencies, risk and digest.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/58-actions-full.png" alt="Action center — full view"><br><b>Action center — full view</b><br><sub>Approval batches, the batch builder and history.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/59-actions-ledger.png" alt="Execution ledger"><br><b>Execution ledger</b><br><sub>Per-action ledger of state transitions, with the exact payload and its SHA-256 digest.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/60-actions-approved-held.png" alt="Approved and held"><br><b>Approved and held</b><br><sub>Approved actions for unconnected providers are held: nothing is sent and the missing credential is named.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/61-actions-builder.png" alt="Action builder and history"><br><b>Action builder and history</b><br><sub>Build a multi-app batch by hand; decided actions and receipts are kept in history.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/62-actions-validation.png" alt="Payload validation"><br><b>Payload validation</b><br><sub>Invalid payloads are refused before they can be proposed.</sub></td></tr>
</table>

### Memory & safety

Six memory layers you can inspect and delete, plus the security controls and a verifiable audit log.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/63-memory-layers.png" alt="Six memory layers"><br><b>Six memory layers</b><br><sub>Working, conversation, episodic, semantic, procedural and preference memory, each inspectable and deletable.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/64-memory-recall.png" alt="Semantic recall test"><br><b>Semantic recall test</b><br><sub>Ranked recall from the local embedding index with similarity scores.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/65-memory-full.png" alt="Memory & safety — full page"><br><b>Memory & safety — full page</b><br><sub>All layers, security controls, security events and the hash-chained audit log.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/66-security-controls.png" alt="Security controls and audit chain"><br><b>Security controls and audit chain</b><br><sub>Active controls, the blocked injection event and audit-chain verification status.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/67-security-sentinel.png" alt="Sentinel and redaction"><br><b>Sentinel and redaction</b><br><sub>Try the sentinel: matched rules are listed and secrets/PII are redacted.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/13-concierge-blocked.png" alt="Concierge — sentinel block"><br><b>Concierge — sentinel block</b><br><sub>A prompt-injection attempt is refused by the sentinel before any tool or model is called.</sub></td></tr>
</table>

### App connections

Every provider with its real status. A provider is shown as connected only after a live check succeeds.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/72-connections.png" alt="Provider registry"><br><b>Provider registry</b><br><sub>Every provider with its real status: connected and verified, ready, configuration required or external handoff.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/73-connections-verified.png" alt="Live verification"><br><b>Live verification</b><br><sub>After live probe calls: providers are only marked connected when a real request succeeded.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/74-connections-needs-setup.png" alt="Configuration required"><br><b>Configuration required</b><br><sub>Credentialed providers list the exact environment variables they need.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/75-connections-social.png" alt="Publishing connectors"><br><b>Publishing connectors</b><br><sub>Write connectors with required scopes; all require approval.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/76-connections-detail.png" alt="Provider detail"><br><b>Provider detail</b><br><sub>Capabilities, limits, retry policy, cache, usage and attribution for one provider.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/77-connections-dining.png" alt="Dining providers and handoffs"><br><b>Dining providers and handoffs</b><br><sub>API providers alongside honest app handoffs (Zomato, Swiggy, OpenTable, Google Maps).</sub></td></tr>
</table>

### Developer view

The compiled agent graph, tool permissions, model routing and measured telemetry.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/68-developer-graph.png" alt="Compiled graph topology"><br><b>Compiled graph topology</b><br><sub>The supervisor and eight specialist subgraphs read from the compiled LangGraph object.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/69-developer-full.png" alt="Developer view — full page"><br><b>Developer view — full page</b><br><sub>Tool allowlists, model routing and measured telemetry from this installation.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/70-developer-mermaid.png" alt="Mermaid source"><br><b>Mermaid source</b><br><sub>Mermaid export of the compiled graph, including subgraph nodes and conditional edges.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/71-developer-telemetry.png" alt="Measured telemetry"><br><b>Measured telemetry</b><br><sub>Tool, provider and model usage measured from real calls. Model rows stay empty until a model is connected.</sub></td></tr>
</table>

### Accounts and devices

Private accounts, and a layout that works on phones and tablets.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/01-sign-in.png" alt="Sign in"><br><b>Sign in</b><br><sub>Session-based sign in. Every workspace below is private to the signed-in account.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/02-sign-in-error.png" alt="Sign-in error"><br><b>Sign-in error</b><br><sub>Failed sign-in returns a clear, non-revealing error.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/03-create-account.png" alt="Create account"><br><b>Create account</b><br><sub>Account creation (PBKDF2-hashed password, HttpOnly SameSite=Strict session cookie).</sub></td><td width="50%" valign="top"><img src="docs/screenshots/84-signed-out.png" alt="Signed out"><br><b>Signed out</b><br><sub>Signing out revokes the server-side session.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/78-mobile-today.png" alt="Mobile — Today"><br><b>Mobile — Today</b><br><sub>The Sunshine layout at 390 px.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/79-mobile-dining.png" alt="Mobile — Food & dining"><br><b>Mobile — Food & dining</b><br><sub>Responsive layout on a phone-sized viewport.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/80-mobile-actions.png" alt="Mobile — Action center"><br><b>Mobile — Action center</b><br><sub>Responsive layout on a phone-sized viewport.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/81-mobile-connections.png" alt="Mobile — App connections"><br><b>Mobile — App connections</b><br><sub>Responsive layout on a phone-sized viewport.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/82-mobile-concierge.png" alt="Mobile — AI concierge"><br><b>Mobile — AI concierge</b><br><sub>Responsive layout on a phone-sized viewport.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/83-tablet-orchestrator.png" alt="Tablet — Orchestrator"><br><b>Tablet — Orchestrator</b><br><sub>Layout at 900 px.</sub></td></tr>
</table>

## Budget and booking

**Plan under a budget.** Give a total and a currency. LifeCanvasOS selects from the results you found or saved (events, dining, travel) the combination with the best match score whose prices add up to no more than your budget, keeping at most one choice per category unless you ask for more. Only prices supplied by the provider are counted. Items without a provider price are listed separately as "price to confirm" and never given an invented amount.

**Book and pay.** How a booking completes depends on what the provider allows:

| What | How it completes | Spend control |
| --- | --- | --- |
| Flights | Amadeus Flight Create Orders, from the Action center after you approve traveller details and the exact fare | The order is refused if the fare exceeds the cap you approved or the currency differs |
| Event tickets | Provider checkout (Ticketmaster link from the result, or BookMyShow / District handoff) | Budget check before handoff; final price is confirmed at checkout |
| Restaurant tables | Provider booking (OpenTable, Zomato, Google Maps handoff) or a reservation request email you approve | Budget check on any supplied price |
| Stays and activities | Provider checkout handoff (Booking.com, Airbnb, MakeMyTrip, Klook, GetYourGuide) | Budget check before handoff |

Ticketing and restaurant platforms do not offer a public purchase API, so LifeCanvasOS does not take card details or charge you itself: payment always happens with the provider. Flight orders use the Amadeus environment you configure (test by default).

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/89-budget-planner.png" alt="Budget planner"><br><b>Budget planner</b><br><sub>Best combination of saved ideas within a budget, from provider-supplied prices.</sub></td></tr>
</table>

API: `POST /api/budget/plan`, and the `amadeus_flight_order` action through `POST /api/actions/propose`. See [Budget and booking](docs/BOOKING.md) and [API](docs/API.md).

## Social agents and video calls

**Agents that plan together.** Once two members are connected, either can start a meetup with a few options (a gig, a dinner, a day trip). Each member's personal agent holds that member's private limits: budget ceiling, free dates, interests and dietary needs. The agents negotiate on their owners' behalf and exchange only a verdict per option (accept or decline, plus a coarse preference rank), never the underlying budget or calendar. The option everyone's agent accepts with the best combined preference becomes the proposal, and it is final only after every participant confirms it. If nothing fits, the agents say so without revealing whose limit ruled an option out.

**Video calls.** Connected members can start a private video call from Circles. It opens an unguessable Jitsi Meet room shared only by the two of you; confirmed meetups get a room for the whole group. Calls are unavailable to members who are not connected or who are blocked.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/85-circles-video-call.png" alt="Video call"><br><b>Video call</b><br><sub>A private video room for two connected members.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/86-meetup-created.png" alt="Plan together"><br><b>Plan together</b><br><sub>Start a meetup with options and your private limits.</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/87-meetup-agents-agreed.png" alt="Agents agreed"><br><b>Agents agreed</b><br><sub>The other member's view after sharing limits: the agents picked the option that fits everyone.</sub></td><td width="50%" valign="top"><img src="docs/screenshots/88-meetup-confirmed.png" alt="Meetup confirmed"><br><b>Meetup confirmed</b><br><sub>Everyone confirmed; a group video call is available.</sub></td></tr>
</table>

Details: [Social agents](docs/SOCIAL_AGENTS.md).

API: `POST /api/meetups`, `POST /api/meetups/{id}/constraints`, `POST /api/meetups/{id}/confirm`, `GET /api/meetups`, `POST /api/community/call`.

## Agent architecture

LifeCanvasOS is a hierarchy of agents built on LangGraph. A supervisor plans the work, specialist agents gather live information in parallel, a critic checks it, and only a separate action agent can write to the outside world, after you approve.

```mermaid
flowchart TD
    U([Your request]) --> R[recall<br/>memory and preferences]
    R --> S{sentinel<br/>safety screen}
    S -- blocked --> X[refuse<br/>no tool or model is called]
    S -- ok --> P[planner<br/>goal to tasks]
    P -- one task each, in parallel --> SP

    subgraph SP [Specialist agents]
        direction LR
        E[Entertainment]
        D[Dining]
        T[Travel]
        C[Culture]
        CM[Community]
        RS[Research]
        CR[Creative]
    end

    SP --> K{critic<br/>grounded and complete?}
    K -- retry, bounded --> SP
    K -- ok --> CO[composer<br/>answer from grounded results]
    CO -- has external writes --> A[Action agent<br/>pauses for approval]
    CO -- nothing to write --> M[consolidate<br/>update memory]
    A -- approve or reject --> M
    X --> M
    M --> O([Answer, cards and receipts])

    SP -. read-only tools .-> G[(Provider gateway<br/>live APIs)]
    A -. approved writes only .-> G
```

### Supervisor

The supervisor is a LangGraph `StateGraph` with typed state. Each step is a node:

| Node | What it does |
| --- | --- |
| **recall** | Loads ranked memories, stated preferences and recent turns for this user |
| **sentinel** | Screens the request for injection and abuse. A blocked request stops here; no tool or model is called |
| **planner** | Turns the goal into a structured plan of tasks, one per specialist. Uses a language model when one is configured, otherwise rules. Entities such as city, dates, cuisine and budget always come from the deterministic extractor |
| **specialists** | Compiled subgraphs mounted as nodes and dispatched in parallel with `Send`, each with a retry policy |
| **critic** | Checks every result card for a provider, a link and a retrieval time, and checks coverage per task. Transient provider failures trigger one bounded re-dispatch |
| **composer** | Writes the answer from grounded results only and builds proposals for any external writes |
| **action** | The approval subgraph. It suspends the run with an interrupt until you decide |
| **consolidate** | Writes conversation, working, episodic, semantic, procedural and preference memory |

Parallel branches merge safely: results are combined by task, so a revision replaces the earlier attempt instead of duplicating it.

### Specialist agents

Each specialist is its own compiled graph with its own tool allowlist. An agent cannot call a tool that is not on its list; the check happens at call time.

| Agent | Loop | Tools it may call | Typical output |
| --- | --- | --- | --- |
| **Entertainment** | resolve → select → act → observe → rank → report | Ticketmaster, MusicBrainz, TheSportsDB, TMDB, iTunes, TVmaze, Spotify, Last.fm, YouTube, ticketing handoffs | Events, fixtures, films, shows, tracks |
| **Dining** | same discovery loop | Google Places, Foursquare, OpenStreetMap, dining handoffs | Restaurants with cuisine, dietary and opening-hour details |
| **Travel** | same discovery loop | Weather, Amadeus flights, destination guides, attractions, travel handoffs | Forecast, flight offers, sights |
| **Culture** | same discovery loop | Open Library, Google Books, Art Institute of Chicago, The Met, Strava, weather, charts | Books, artworks, activity |
| **Community** | same discovery loop | Community matching only | Opted-in members with shared interests |
| **Research** | plan queries → parallel search → extract → aggregate → synthesise → verify → revise or report | Tavily, Wikipedia, DuckDuckGo, Wikimedia Commons | A cited answer; claims not found in a source are dropped |
| **Creative** | research → ideate → outline → draft → adapt → critique → revise or propose | Wikipedia, Tavily, Wikimedia Commons | Drafts per platform and publication proposals; it cannot publish |
| **Action** | prepare → gate → decide → execute → verify | Write adapters, and nothing else | Receipts for approved actions |

In the discovery loop, `select` chooses tools and skips providers that are not connected with a visible notice, `act` runs the chosen tools concurrently under a per-tool deadline, and `observe` decides whether one more round is needed (at most two).

### Workflows

A workflow presets which specialists run. `auto` lets the planner choose.

| Workflow | Specialists |
| --- | --- |
| Weekend planner | Entertainment, Dining, Travel |
| Evening out | Dining, Entertainment |
| Trip builder | Travel, Dining, Culture |
| Match day | Entertainment, Dining |
| Wellness day | Culture, Travel |
| Find my people | Community, Entertainment |
| Deep research | Research |
| Create & publish | Creative |

### Why writes are separate

- Research and discovery agents hold read-only tools. Text they retrieve is treated as data, never as instructions.
- Write adapters are reachable only from the action agent, and only for a payload you approved. The approval is tied to a digest of that payload, works once and expires.
- A write is never retried automatically. If the outcome is uncertain it is recorded as unknown.

### Social agents

Meetup planning uses a second, simpler kind of agent: one per member, holding that member's private limits and answering only accept or decline per option. They run as a deterministic service outside the supervisor graph. See [Social agents](docs/SOCIAL_AGENTS.md).

### Runtime, models and memory

- **Durable runs.** Each run is one LangGraph thread checkpointed to SQLite. Runs stream events live, pause for approval, resume, can be cancelled, and recover after a restart.
- **Limits.** 150 seconds per run, 14 seconds per tool call and three concurrent runs per user.
- **Provider gateway.** Pooled async HTTP with rate limits, caching, retries for reads only, circuit breakers and host allowlists.
- **Model routing.** OpenAI, Anthropic, Gemini, OpenRouter, Groq and Ollama, ordered by a balanced, quality, cost or latency strategy with automatic fallback. With no model configured, agents use their rule-based path and the UI says so.
- **Six-layer memory.** Working, conversation, episodic, semantic, procedural and preferences, recalled by similarity, recency and reinforcement, and scoped to one user.

More detail: [Architecture](docs/ARCHITECTURE.md).

## Get started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # optional: add provider keys
uvicorn app.main:app --port 8000
```

Open http://localhost:8000 and create an account. Fifteen live sources work with no keys at all, including Open-Meteo, OpenStreetMap, iTunes, MusicBrainz, TheSportsDB, TVmaze, Open Library, the Art Institute of Chicago, The Met, Wikipedia and Wikivoyage.

With Docker:

```bash
docker compose up --build
```

## Connect your apps

Add keys to `.env` (every variable is listed in [.env.example](.env.example)). A provider moves from "configuration required" to "ready", and to "connected" once a live check succeeds.

| Area | Providers |
| --- | --- |
| Events and entertainment | Ticketmaster, TMDB, Spotify, YouTube, Last.fm |
| Places | Google Places, Foursquare |
| Travel | Amadeus (flight offers and orders), OpenTripMap, GeoNames |
| Research | Tavily |
| Publishing | X, LinkedIn, Instagram, Facebook Pages, Bluesky, Mastodon, WordPress, Telegram, Discord, Slack |
| Productivity | Gmail, Google Calendar, Google Tasks, Google Drive, Notion, Todoist, Microsoft To Do, Spotify playlists |
| Language models | OpenAI, Anthropic, Gemini, OpenRouter, Groq, Ollama |
| App handoffs | BookMyShow, District, Zomato, Swiggy, OpenTable, Google Maps, Airbnb, MakeMyTrip, Booking.com, Uber, Klook, GetYourGuide, Tripadvisor, Google Flights |

Full matrix: [Integrations](docs/INTEGRATIONS.md).

## Security and privacy

- Private accounts with hashed passwords and HttpOnly, SameSite=Strict sessions.
- Every external action needs approval tied to a fingerprint of the exact content, works once and expires.
- If an outcome is uncertain it is marked unknown and never retried automatically.
- Search and research agents cannot reach any tool that writes, books or pays.
- Text from providers is treated as data; instruction-like content is withheld.
- Secrets and personal details are redacted before anything is stored. Delete a memory, a layer or your whole account at any time.

Details: [Security](docs/SECURITY.md).

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Integrations](docs/INTEGRATIONS.md) · [Budget and booking](docs/BOOKING.md) · [Social agents](docs/SOCIAL_AGENTS.md) · [Security](docs/SECURITY.md) · [API](docs/API.md) · [Deployment](docs/DEPLOYMENT.md) · [Evaluation](docs/EVALUATION.md) · [Gallery](docs/GALLERY.md)

## License

MIT

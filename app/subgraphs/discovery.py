"""Discovery specialists: entertainment, dining, travel, community, culture.

Each specialist is an independently compiled LangGraph subgraph running a bounded ReAct loop:

    resolve -> select -> act -> observe -+-> rank -> report
                  ^----------------------+   (at most MAX_ITERATIONS passes)

`select` is the reasoning step (a tool policy over the agent's allowlist), `act` executes the chosen tools in
parallel under deadlines, `observe` decides whether evidence is sufficient or fallbacks are needed.
"""
from __future__ import annotations

import asyncio
import re
from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.integrations import geo
from app.providers.base import ProviderError
from app.services.container import Services
from app.state import SpecialistOutput, SpecialistState, step
from app.tools import registry as tools

MAX_ITERATIONS = 2
Call = dict  # {"tool": str, "args": dict}


def _c(tool: str, **args) -> Call:
    return {"tool": tool, "args": args}


# ------------------------------------------------------------------ tool policies (one per specialist)
def entertainment_policy(s: SpecialistState, it: int) -> list[Call]:
    p, t = s["task"]["params"], s["task"]
    city, country = p.get("city", ""), p.get("country", "")
    genre = (p.get("genres") or [""])[0]
    topic = p.get("topic") or genre or t.get("query", "")
    out: list[Call] = []
    if it == 0:
        if p.get("sport") or p.get("team"):
            out.append(_c("sports_fixtures", sport=p.get("sport") or "football", team=p.get("team", "")))
        if p.get("wants_events") or not (p.get("sport") or p.get("team") or p.get("wants_movies") or p.get("wants_shows") or p.get("wants_music")):
            out += [_c("events_ticketmaster", query=topic, city=city, country=country), _c("events_musicbrainz", query=topic or "festival", city=city)]
        if p.get("wants_movies"):
            out += [_c("movies_tmdb", query=p.get("topic", ""), trending=not p.get("topic")), _c("movies_charts", country=(country or "us").lower())]
        if p.get("wants_shows") and topic:
            out.append(_c("shows_tvmaze", query=topic))
        if p.get("wants_music") and topic:
            out += [_c("music_spotify", query=topic), _c("music_itunes", query=topic, country=country), _c("artists_musicbrainz", query=topic)]
            if p.get("topic"):
                out += [_c("artists_lastfm", query=p["topic"]), _c("videos_youtube", query=topic + " live")]
        if city and (p.get("wants_events") or p.get("wants_movies")):
            out.append(_c("handoff_entertainment", query=topic or "events", city=city))
    else:  # widen: drop the city constraint, fall back to open catalogues
        if p.get("wants_events") or not out:
            out.append(_c("events_musicbrainz", query=topic or genre or "festival", city=""))
        if topic:
            out.append(_c("music_itunes", query=topic))
        out.append(_c("movies_charts", country="us"))
    return out


def dining_policy(s: SpecialistState, it: int) -> list[Call]:
    p = s["task"]["params"]
    city = p.get("city", "")
    cuisine = next((c for c in p.get("cuisines", []) if c not in p.get("diets", [])), "")
    amenity = p.get("amenity", "restaurant")
    query = " ".join(x for x in (*p.get("diets", []), cuisine, amenity.replace("_", " ")) if x)
    if it == 0:
        return [_c("places_google", query=query, city=city), _c("places_foursquare", query=query, city=city, place=s.get("place")),
                _c("places_osm", city=city, place=s.get("place"), amenity=amenity, cuisine=cuisine, radius_m=4000), _c("handoff_dining", query=query, city=city)]
    return [_c("places_osm", city=city, place=s.get("place"), amenity=amenity, cuisine="", radius_m=9000, area=city)]


def travel_policy(s: SpecialistState, it: int) -> list[Call]:
    p = s["task"]["params"]
    dest = p.get("destination") or p.get("city", "")
    if it == 0:
        out = [_c("weather", city=dest), _c("destination_guide", query=dest), _c("attractions", city=dest, place=s.get("place"))]
        if p.get("wants_flights"):
            out.append(_c("flights_amadeus", origin=p.get("origin", ""), destination=dest, date=(p.get("when") or {}).get("start", "")))
        route = f"{p.get('origin', '')} to {dest}".strip()
        return out + [_c("handoff_travel", query=f"Flights from {route}" if p.get("origin") else dest, city=dest)]
    return [_c("destination_guide", query=dest.split(",")[0].split()[0])] if dest else []


def community_policy(s: SpecialistState, it: int) -> list[Call]:
    p = s["task"]["params"]
    interests = [*p.get("genres", []), *p.get("cuisines", []), *([p["sport"]] if p.get("sport") else []), *p.get("interests", [])]
    return [_c("community_matches", interests=interests or None, city=p.get("city", ""))] if it == 0 else []


def culture_policy(s: SpecialistState, it: int) -> list[Call]:
    p, t = s["task"]["params"], s["task"]
    topic = p.get("topic") or t.get("query", "")
    none = not (p.get("wants_books") or p.get("wants_art") or p.get("wants_fitness"))
    if it == 0:
        out: list[Call] = []
        if p.get("wants_books") or none:
            out += [_c("books_openlibrary", query=topic), _c("books_google", query=topic)]
        if p.get("wants_art") or none:
            out += [_c("artworks_artic", query=topic), _c("artworks_met", query=topic)]
        if p.get("wants_fitness"):
            out += [_c("fitness_strava"), _c("weather", city=p.get("city", ""))]
        return out
    short = " ".join(topic.split()[:2])
    return [_c("books_openlibrary", query=short), _c("artworks_artic", query=short)] if short and short != topic else []


POLICIES: dict[str, Callable[[SpecialistState, int], list[Call]]] = {
    "entertainment": entertainment_policy, "dining": dining_policy, "travel": travel_policy, "community": community_policy, "culture": culture_policy}
NEEDS_PLACE = {"dining", "travel"}


# ------------------------------------------------------------------ ranking
def _score(card: dict, prefs: dict, p: dict) -> tuple[float, list[str]]:
    text = f"{card['title']} {card['summary']} {' '.join(card['tags'])} {card['meta'].get('cuisine', '')}".lower()
    score, why = 0.0, []
    for kind, weight in (("cuisine", 2.0), ("artist", 3.0), ("team", 3.0), ("travel_style", 1.0)):
        for value in prefs.get(kind, []):
            if value.lower() in text:
                score += weight
                why.append(f"matches your {kind.replace('_', ' ')} preference ({value})")
    for value in (*p.get("cuisines", []), *p.get("genres", [])):
        if value in text:
            score += 1.5
    diets = {d.lower().replace(" ", "_").replace("-", "_") for d in (*p.get("diets", []), *prefs.get("diet", []))}
    if diets and card["kind"] == "place":
        tagged = set(card["meta"].get("diet", []))
        if diets & tagged or any(d.replace("_", " ") in text for d in diets):
            score += 3
            why.append("dietary option listed by the source")
        else:
            card["meta"]["diet_note"] = "Dietary suitability is not stated by the source; confirm with the venue."
    budget = p.get("budget") or {}
    if budget and card["price"] is not None:
        if card["price"] <= budget["amount"]:
            score += 1
            why.append("within your stated budget")
        else:
            score -= 2
    start = (p.get("when") or {}).get("start")
    if start and card["when"][:10] and card["kind"] in ("event", "fixture"):
        end = p["when"].get("end", start)
        if start <= card["when"][:10] <= end:
            score += 3
            why.append(f"happening {p['when']['label']}")
        elif card["when"][:10] < start:
            score -= 1
    score += 0.4 * bool(card["image"]) + 0.3 * bool(card["rating"]) + (0.2 * card["rating"] / 5 if card["rating"] and card["rating"] <= 5 else 0)
    if card["availability"] == "past record":
        score -= 4
    return score, why


def build(domain: str, svc: Services):
    """Compile one discovery specialist as an independent subgraph."""
    policy = POLICIES[domain]

    async def resolve(s: SpecialistState) -> dict:
        p = s["task"]["params"]
        target = (p.get("destination") or p.get("city")) if domain == "travel" else p.get("city")
        if domain not in NEEDS_PLACE or not target:
            return {"iteration": 0, "trace": [step(f"{domain}.resolve", "Parameters resolved from the plan", params=sorted(k for k, v in p.items() if v))]}
        try:
            place = await geo.geocode(svc.gateway, target, p.get("country", "") if target == p.get("city") else "")
        except ProviderError as exc:
            return {"iteration": 0, "notices": [{"provider": exc.provider, "error_class": exc.kind, "message": str(exc), "tool": "geocode"}],
                    "trace": [step(f"{domain}.resolve", f"Could not locate '{target}'", error=exc.kind)]}
        return {"iteration": 0, "place": place, "trace": [step(f"{domain}.resolve", f"Located {place['name']}, {place['admin']} via {place['provider']}", lat=place["lat"], lon=place["lon"])]}

    async def select(s: SpecialistState) -> dict:
        it = s.get("iteration", 0)
        queue, notices, seen = [], [], set(s.get("tried", []))
        for call in policy(s, it):
            key = call["tool"] + ":" + repr(sorted((k, str(v)) for k, v in call["args"].items() if k != "place"))
            if key in seen or call["tool"] not in tools.ALLOW[domain]:
                continue
            seen.add(key)
            spec = svc.gateway.specs.get(tools.TOOLS[call["tool"]].provider)
            if spec is not None and spec.env and not spec.configured:  # do not call; report honestly
                if it == 0:
                    notices.append({"provider": spec.name, "provider_id": spec.id, "error_class": "config", "tool": call["tool"],
                                    "message": f"{spec.name} is not connected. Add {', '.join(spec.env)} in App Connections to enable it."})
                continue
            queue.append(call | {"key": key})
        return {"queue": queue, "notices": notices, "tried": [c["key"] for c in queue],
                "trace": [step(f"{domain}.select", f"Pass {it + 1}: selected {len(queue)} tool(s)" + (f", {len(notices)} provider(s) need configuration" if notices else ""), tools=[c["tool"] for c in queue])]}

    async def act(s: SpecialistState) -> dict:
        ctx = svc.tool_ctx(s["user_id"], s.get("run_id", ""))
        obs = await asyncio.gather(*(tools.call(ctx, domain, c["tool"], c["args"]) for c in s.get("queue", [])))
        return {"observations": list(obs), "queue": [],
                "trace": [step(f"{domain}.act", f"{o['tool']}: " + (f"{len(o['cards'])} result(s)" if o["ok"] else f"failed ({o['error']['error_class']})"), provider=o["provider"], latency_ms=o["latency_ms"], ok=o["ok"]) for o in obs]}

    async def observe(s: SpecialistState) -> dict:
        real = sum(len(o["cards"]) for o in s.get("observations", []) if o["ok"] and not o["tool"].startswith("handoff_"))
        return {"iteration": s.get("iteration", 0) + 1,
                "trace": [step(f"{domain}.observe", f"{real} grounded result(s) so far" + ("; evidence is sufficient" if real else "; trying fallbacks" if s.get("iteration", 0) + 1 < MAX_ITERATIONS else "; no further fallbacks"))]}

    def route(s: SpecialistState) -> str:
        real = sum(len(o["cards"]) for o in s.get("observations", []) if o["ok"] and not o["tool"].startswith("handoff_"))
        if real == 0 and s.get("iteration", 0) < MAX_ITERATIONS and policy(s, s.get("iteration", 0)):
            return "select"
        return "rank"

    async def rank(s: SpecialistState) -> dict:
        prefs, p = s.get("preferences") or {}, s["task"]["params"]
        seen, cards, handoffs = set(), [], []
        for o in s.get("observations", []):
            for c in o["cards"]:
                key = (c["kind"], re.sub(r"\W+", "", c["title"].lower()))
                if key in seen:
                    continue
                seen.add(key)
                if c["kind"] == "handoff":
                    handoffs.append(c)
                    continue
                c["score"], c["why"] = _score(c, prefs, p)
                cards.append(c)
        cards.sort(key=lambda c: -c["score"])
        return {"cards": cards[:24], "extra": {"handoffs": handoffs},
                "trace": [step(f"{domain}.rank", f"Ranked {len(cards)} result(s)" + (f"; {sum(1 for c in cards if c['why'])} personalised" if any(c["why"] for c in cards) else ""))]}

    async def report(s: SpecialistState) -> dict:
        obs = s.get("observations", [])
        errors = [o["error"] | {"tool": o["tool"]} for o in obs if not o["ok"]]
        result = {"task_id": s["task"]["id"], "specialist": domain, "objective": s["task"]["objective"], "cards": s.get("cards", []), "handoffs": (s.get("extra") or {}).get("handoffs", []),
                  "errors": errors, "notices": s.get("notices", []), "place": s.get("place"), "iterations": s.get("iteration", 0),
                  "tools": [{"tool": o["tool"], "provider": o["provider"], "ok": o["ok"], "items": len(o["cards"]), "latency_ms": o["latency_ms"]} for o in obs],
                  "flagged": sum(o["flagged"] for o in obs), "status": "ok" if s.get("cards") else ("needs_configuration" if s.get("notices") and not errors else "no_results" if not errors else "failed")}
        return {"results": [result], "trace": [step(f"{domain}.report", f"{domain.title()} specialist finished: {result['status']}, {len(result['cards'])} card(s)")]}

    g = StateGraph(SpecialistState, output_schema=SpecialistOutput)
    for name, fn in (("resolve", resolve), ("select", select), ("act", act), ("observe", observe), ("rank", rank), ("report", report)):
        g.add_node(name, fn)
    g.add_edge(START, "resolve")
    g.add_edge("resolve", "select")
    g.add_edge("select", "act")
    g.add_edge("act", "observe")
    g.add_conditional_edges("observe", route, {"select": "select", "rank": "rank"})
    g.add_edge("rank", "report")
    g.add_edge("report", END)
    return g.compile(name=f"{domain}_specialist")

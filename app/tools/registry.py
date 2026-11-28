"""Tool registry with per-agent least-privilege allowlists.

Discovery tools are read-only. Transactional tools are registered in a separate table (`WRITE_TOOLS`) that only the
Action execution graph can resolve; no research or discovery specialist can reach them, by construction.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.integrations import culture, geo, handoffs, places, publish, research, travel
from app.integrations import entertainment as ent
from app.providers.base import Gateway, ProviderError
from app.repositories.db import Database, now
from app.schemas.cards import card
from app.security import isolate


@dataclass
class ToolContext:
    gw: Gateway
    db: Database | None
    user_id: str
    run_id: str
    community: Any = None
    deadline_s: float = 14.0


@dataclass(frozen=True)
class Tool:
    name: str
    provider: str
    description: str
    fn: Callable[[ToolContext, dict], Awaitable[list[dict]]]
    scope: str = "read"


async def _places_osm(c: ToolContext, a: dict) -> list[dict]:
    place = a.get("place") or await geo.geocode(c.gw, a["city"], a.get("country", ""))
    return await places.osm_places(c.gw, place["lat"], place["lon"], a.get("amenity", "restaurant"), a.get("cuisine", ""), a.get("radius_m", 4000), a.get("area") or place["name"])


async def _places_fsq(c: ToolContext, a: dict) -> list[dict]:
    c.gw.require("foursquare")
    place = a.get("place") or await geo.geocode(c.gw, a["city"], a.get("country", ""))
    return await places.foursquare_places(c.gw, a["query"], place["lat"], place["lon"])


async def _attractions(c: ToolContext, a: dict) -> list[dict]:
    place = a.get("place") or await geo.geocode(c.gw, a["city"], a.get("country", ""))
    return await travel.attractions(c.gw, place["lat"], place["lon"])


async def _flights(c: ToolContext, a: dict) -> list[dict]:
    c.gw.require("amadeus")
    o, d = travel.iata(a.get("origin", "")), travel.iata(a.get("destination", ""))
    if not o or not d or not a.get("date"):
        raise ProviderError("amadeus", "bad_request", "Flight search needs an origin, destination and departure date (YYYY-MM-DD)")
    return await travel.flight_offers(c.gw, o, d, a["date"], a.get("adults", 1))


async def _community(c: ToolContext, a: dict) -> list[dict]:
    rows = c.community.matches(c.user_id, a.get("interests"), a.get("city", ""))
    return [card("lifecanvas", "member", m["display_name"], "", where=m["city"], summary=m["bio"], tags=m["interests"][:6], user_id=m["user_id"], shared=m["shared"],
                 match_score=m["score"], same_city=m["same_city"], connection=m["connection"]) | {"provider": "LifeCanvas community", "attribution": "Opted-in LifeCanvas members"} for m in rows]


async def _handoff(domain: str, c: ToolContext, a: dict) -> list[dict]:
    return handoffs.handoffs(domain, a.get("query", ""), a.get("city", ""))


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("events_ticketmaster", "ticketmaster", "Upcoming ticketed events by keyword and city", lambda c, a: ent.ticketmaster_events(c.gw, a.get("query", ""), a.get("city", ""), a.get("country", ""), a.get("segment", ""))),
    Tool("events_musicbrainz", "musicbrainz", "Community-recorded concerts and festivals", lambda c, a: ent.musicbrainz_events(c.gw, a.get("query", ""), a.get("city", ""))),
    Tool("sports_fixtures", "thesportsdb", "Upcoming fixtures by sport or team", lambda c, a: ent.sports_fixtures(c.gw, a.get("sport", "football"), a.get("team", ""))),
    Tool("movies_tmdb", "tmdb", "Movie search and weekly trending", lambda c, a: ent.tmdb_movies(c.gw, a.get("query", ""), a.get("trending", False))),
    Tool("movies_charts", "itunes", "Current top movie chart for a storefront", lambda c, a: ent.itunes_top_movies(c.gw, a.get("country", "us") or "us")),
    Tool("shows_tvmaze", "tvmaze", "TV show search", lambda c, a: ent.tvmaze_shows(c.gw, a["query"])),
    Tool("music_itunes", "itunes", "Track search with previews", lambda c, a: ent.itunes_music(c.gw, a["query"], "song", a.get("country", ""))),
    Tool("music_spotify", "spotify", "Spotify catalogue search", lambda c, a: ent.spotify_search(c.gw, a["query"], a.get("kind", "track"))),
    Tool("artists_musicbrainz", "musicbrainz", "Artist identity and genre tags", lambda c, a: ent.musicbrainz_artist(c.gw, a["query"])),
    Tool("artists_lastfm", "lastfm", "Similar artists", lambda c, a: ent.lastfm_similar(c.gw, a["query"])),
    Tool("videos_youtube", "youtube", "Video search", lambda c, a: ent.youtube_videos(c.gw, a["query"])),
    Tool("places_google", "google_places", "Restaurant and place text search with ratings", lambda c, a: places.google_places(c.gw, a["query"], a["city"])),
    Tool("places_foursquare", "foursquare", "Nearby venues", _places_fsq),
    Tool("places_osm", "overpass", "OpenStreetMap restaurants, cafes and bars near a point", _places_osm),
    Tool("weather", "open_meteo", "Current weather and daily forecast", lambda c, a: geo.weather(c.gw, a["city"], a.get("country", ""))),
    Tool("flights_amadeus", "amadeus", "Flight offers with prices", _flights),
    Tool("destination_guide", "wikivoyage", "Destination overviews", lambda c, a: travel.destination_guide(c.gw, a["query"])),
    Tool("attractions", "wikipedia", "Landmarks near a city", _attractions),
    Tool("books_openlibrary", "openlibrary", "Book search", lambda c, a: culture.books(c.gw, a["query"])),
    Tool("books_google", "google_books", "Book search with sale info", lambda c, a: culture.google_books(c.gw, a["query"])),
    Tool("artworks_artic", "artic", "Art Institute of Chicago collection", lambda c, a: culture.artworks(c.gw, a["query"])),
    Tool("artworks_met", "met_museum", "The Met collection", lambda c, a: culture.met_artworks(c.gw, a["query"])),
    Tool("fitness_strava", "strava", "The owner's recent activities", lambda c, a: culture.strava_activities(c.gw)),
    Tool("web_tavily", "tavily", "Web search with extracted content", lambda c, a: research.tavily_search(c.gw, a["query"], a.get("deep", False))),
    Tool("wikipedia_search", "wikipedia", "Encyclopedia search", lambda c, a: research.wikipedia_search(c.gw, a["query"])),
    Tool("wikipedia_summary", "wikipedia", "Encyclopedia article summary", lambda c, a: research.wikipedia_summary(c.gw, a["query"])),
    Tool("instant_answer", "duckduckgo", "Instant answers and related topics", lambda c, a: research.instant_answer(c.gw, a["query"])),
    Tool("images_commons", "commons", "Freely licensed images", lambda c, a: research.commons_images(c.gw, a["query"])),
    Tool("community_matches", "lifecanvas", "Opted-in members with shared interests", _community),
    Tool("handoff_entertainment", "bookmyshow", "Ticketing app deep links", lambda c, a: _handoff("entertainment", c, a)),
    Tool("handoff_dining", "zomato", "Dining app deep links", lambda c, a: _handoff("dining", c, a)),
    Tool("handoff_travel", "google_flights", "Travel app deep links", lambda c, a: _handoff("travel", c, a)),
]}

# Least-privilege allowlists. `action` is deliberately absent: it has no discovery tools.
ALLOW: dict[str, frozenset[str]] = {
    "entertainment": frozenset({"events_ticketmaster", "events_musicbrainz", "sports_fixtures", "movies_tmdb", "movies_charts", "shows_tvmaze", "music_itunes", "music_spotify",
                                "artists_musicbrainz", "artists_lastfm", "videos_youtube", "handoff_entertainment"}),
    "dining": frozenset({"places_google", "places_foursquare", "places_osm", "handoff_dining"}),
    "travel": frozenset({"weather", "flights_amadeus", "destination_guide", "attractions", "handoff_travel"}),
    "community": frozenset({"community_matches"}),
    "culture": frozenset({"books_openlibrary", "books_google", "artworks_artic", "artworks_met", "fitness_strava", "weather", "movies_charts", "music_itunes"}),
    "research": frozenset({"web_tavily", "wikipedia_search", "wikipedia_summary", "instant_answer", "images_commons"}),
    "creative": frozenset({"wikipedia_search", "wikipedia_summary", "web_tavily", "images_commons"}),
}
WRITE_TOOLS: frozenset[str] = frozenset(publish.EXTERNAL)


class ToolDenied(Exception):
    pass


async def call(ctx: ToolContext, agent: str, name: str, args: dict) -> dict:
    """Run one read tool for an agent. Returns an observation; never raises for provider failures."""
    if name not in ALLOW.get(agent, frozenset()) or name not in TOOLS:
        raise ToolDenied(f"Agent '{agent}' is not permitted to call '{name}'")
    tool, started = TOOLS[name], time.monotonic()
    obs = {"tool": name, "provider": tool.provider, "args": {k: v for k, v in args.items() if k != "place"}, "ok": False, "cards": [], "error": None, "flagged": 0}
    try:
        cards = await asyncio.wait_for(tool.fn(ctx, args), ctx.deadline_s)
        clean = []
        for c in cards:  # retrieved text is untrusted data: neutralise instruction-like content before any agent sees it
            _, bad_s = isolate(c["summary"])
            _, bad_t = isolate(c["title"])
            if bad_s or bad_t:
                obs["flagged"] += 1
                c["meta"]["untrusted_content_filtered"] = True
                c["summary"] = "Text withheld: this source contained instruction-like content. Open the source link to read it."
                if bad_t:
                    c["title"] = "Untitled source (title withheld)"
            clean.append(c)
        obs.update(ok=True, cards=clean)
    except ProviderError as exc:
        obs["error"] = exc.public()
    except TimeoutError:
        obs["error"] = {"provider": tool.provider, "error_class": "deadline", "message": f"{name} exceeded the {ctx.deadline_s:.0f}s tool deadline"}
    except (KeyError, TypeError, ValueError) as exc:
        obs["error"] = {"provider": tool.provider, "error_class": "bad_request", "message": f"{name}: missing or invalid argument ({type(exc).__name__}: {exc})"}
    obs["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
    if ctx.db is not None:
        ctx.db.run("INSERT INTO tool_calls(run_id,user_id,agent,tool,provider,ok,items,latency_ms,error,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (ctx.run_id, ctx.user_id, agent, name, tool.provider, int(obs["ok"]), len(obs["cards"]), obs["latency_ms"], (obs["error"] or {}).get("error_class", ""), now()))
    return obs


def catalog() -> list[dict]:
    return [{"name": t.name, "provider": t.provider, "description": t.description, "scope": "read", "agents": sorted(a for a, s in ALLOW.items() if t.name in s)} for t in TOOLS.values()] + \
           [{"name": "execute:" + k, "provider": k, "description": "Approved external write", "scope": "write", "agents": ["action"]} for k in sorted(WRITE_TOOLS)]

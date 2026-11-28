"""Deterministic request understanding used when no language model is configured (and as a validator when one is).

It extracts explicit entities only: location, cuisine, dietary need, genre, sport, team, dates and budget. It does
not guess. The planner labels its output `rules` so the UI never presents this path as model reasoning.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

CUISINES = ("south indian", "north indian", "italian", "chinese", "japanese", "thai", "mexican", "korean", "indian", "mughlai", "french", "vietnamese", "mediterranean", "lebanese",
            "american", "spanish", "greek", "turkish", "continental", "asian", "sushi", "pizza", "burger", "biryani", "ramen", "seafood", "barbecue", "bbq", "dessert", "vegan", "vegetarian", "kebab", "tibetan", "bengali")
DIETS = ("vegetarian", "vegan", "gluten-free", "gluten free", "halal", "kosher", "jain", "pescatarian")
GENRES = ("jazz", "rock", "pop", "indie", "classical", "hip hop", "hip-hop", "electronic", "techno", "edm", "metal", "blues", "folk", "bollywood", "sufi", "ghazal", "k-pop", "country", "reggae", "punk", "soul", "house", "carnatic", "hindustani", "opera", "lo-fi", "ambient", "r&b", "latin")
SPORTS = {"football": ("football", "soccer", "premier league", "la liga", "champions league"), "cricket": ("cricket", "ipl", "test match", "t20", "odi"), "basketball": ("basketball", "nba")}
AMENITIES = {"cafe": ("cafe", "café", "coffee", "brunch"), "bar": ("bar ", "bars", "cocktail", "drinks", "pub"), "fast_food": ("fast food", "takeaway", "street food"), "restaurant": ("restaurant", "dinner", "lunch", "dining", "eat", "food", "meal", "supper")}
DOMAIN_WORDS = {
    "dining": ("restaurant", "dinner", "lunch", "brunch", "breakfast", "cafe", "café", "coffee", "eat", "food", "dining", "cuisine", "bar ", "cocktail", "table for", "meal", *CUISINES),
    "entertainment": ("concert", "gig", "live music", "festival", "show", "movie", "film", "cinema", "theatre", "theater", "comedy", "stand-up", "match", "game", "fixture", "sport", "music", "song", "playlist", "artist", "band",
                      "album", "series", "tv ", "event", "tickets", "watch", "listen", *GENRES, *[w for ws in SPORTS.values() for w in ws]),
    "travel": ("trip", "travel", "flight", "fly", "itinerary", "getaway", "escape", "vacation", "holiday", "weekend in", "visit", "hotel", "stay", "weather", "forecast", "attractions", "sightseeing", "things to do", "road trip", "destination"),
    "community": ("meet people", "find people", "buddies", "buddy", "circle", "community", "like-minded", "connect with", "friends who", "group for", "club", "members", "people who"),
    "culture": ("book", "read", "novel", "museum", "art", "artwork", "painting", "gallery", "exhibition", "run", "running", "cycling", "cycle", "ride", "workout", "fitness", "wellness", "yoga", "meditat", "hike", "walk", "strava"),
    "research": ("research", "compare", "explain", "why ", "how does", "how do", "what is", "what are", "who is", "history of", "sources", "evidence", "cite", "learn about", "tell me about", "deep dive", "facts"),
    "creative": ("write", "draft", "blog", "post", "caption", "tweet", "thread", "newsletter", "article", "linkedin", "instagram", "announce", "publish", "story about", "copy for", "essay"),
    "action": ("post it", "publish", "send", "email", "schedule", "add to my calendar", "calendar", "remind", "task", "todo", "to-do", "share on", "share to", "notify", "message", "create a playlist", "save to notion", "invite"),
}
PLATFORMS = {"x": ("twitter", " x ", "tweet", "on x"), "linkedin": ("linkedin",), "instagram": ("instagram", "insta"), "facebook": ("facebook",), "bluesky": ("bluesky",), "mastodon": ("mastodon",),
             "wordpress": ("wordpress", "blog"), "telegram": ("telegram",), "discord": ("discord",), "slack": ("slack",), "gmail": ("email", "gmail", "mail to"), "google_calendar": ("calendar",),
             "google_tasks": ("google tasks",), "todoist": ("todoist",), "notion": ("notion",), "ms_graph": ("microsoft to do", "outlook task"), "google_drive": ("google doc", "drive"),
             "spotify_playlist": ("playlist",)}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
NOT_PLACES = {"The", "A", "My", "This", "Next", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",
              "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Advance", "Time", "Person", "General", "English", "Hindi", "Spotify", "Notion", "Slack", "Linkedin", "Instagram"}
PLACE_RE = re.compile(r"\b(?:in|at|near|around|to|visit(?:ing)?|from|for)\s+((?:[A-Z][\w'’-]+)(?:\s+(?:[A-Z][\w'’-]+|de|del|la|el)){0,3})")
FROM_TO_RE = re.compile(r"\bfrom\s+([A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+)?)\s+to\s+([A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+)?)")
TEAM_RE = re.compile(r"\b((?:[A-Z][\w']+\s){0,2}(?:FC|United|City|Arsenal|Chelsea|Liverpool|Tottenham|Barcelona|Madrid|Juventus|Bayern|Lakers|Warriors|Celtics|Knicks|Indians|Super Kings|Royal Challengers|Knight Riders))\b")
QUOTED_RE = re.compile(r"[\"“']([^\"”']{2,80})[\"”']")
ABOUT_RE = re.compile(r"\b(?:about|on|regarding|for|of)\s+(.{3,120}?)(?:\s+(?:for|on|to|and (?:post|publish|share|send))\s+(?:my\s+)?(?:twitter|x|linkedin|instagram|facebook|blog|bluesky|mastodon|slack|discord|telegram|wordpress)\b|[.?!]|$)", re.I)
BUDGET_RE = re.compile(r"(₹|rs\.?|inr|\$|usd|€|eur|£)\s?([\d,]+)\s?(k)?", re.I)


def find(text: str, vocabulary) -> list[str]:
    low = f" {text.lower()} "
    return [w for w in vocabulary if re.search(rf"(?<![a-z]){re.escape(w.strip())}(?![a-z])", low)]


def when(text: str, today: date | None = None) -> dict:
    today, low = today or date.today(), text.lower()
    m = re.search(r"\b(20\d\d-\d\d-\d\d)\b", text)
    if m:
        return {"label": m.group(1), "start": m.group(1), "end": m.group(1)}
    if "tonight" in low or "today" in low:
        return {"label": "today", "start": today.isoformat(), "end": today.isoformat()}
    if "tomorrow" in low:
        d = today + timedelta(days=1)
        return {"label": "tomorrow", "start": d.isoformat(), "end": d.isoformat()}
    if "weekend" in low:
        sat = today + timedelta(days=(5 - today.weekday()) % 7 + (7 if "next weekend" in low else 0))
        return {"label": "next weekend" if "next weekend" in low else "this weekend", "start": sat.isoformat(), "end": (sat + timedelta(days=1)).isoformat()}
    for i, day in enumerate(WEEKDAYS):
        if day in low:
            d = today + timedelta(days=(i - today.weekday()) % 7 or 7)
            return {"label": day.title(), "start": d.isoformat(), "end": d.isoformat()}
    if "next week" in low:
        d = today + timedelta(days=7 - today.weekday())
        return {"label": "next week", "start": d.isoformat(), "end": (d + timedelta(days=6)).isoformat()}
    return {}


def understand(goal: str, default_city: str = "", default_country: str = "") -> dict:
    low = f" {goal.lower()} "
    scores = {d: len(find(goal, words)) for d, words in DOMAIN_WORDS.items()}
    places_found = [p for p in (m.group(1).strip() for m in PLACE_RE.finditer(goal)) if p.split()[0] not in NOT_PLACES]
    route = FROM_TO_RE.search(goal)
    sport = next((s for s, words in SPORTS.items() if find(goal, words)), "")
    team = TEAM_RE.search(goal)
    budget = BUDGET_RE.search(goal)
    quoted = QUOTED_RE.search(goal)
    about = ABOUT_RE.search(goal)
    city = (route.group(2) if route else (places_found[0] if places_found else "")) or default_city
    topic = (quoted.group(1) if quoted else (about.group(1) if about else "")).strip(" .,")
    topic = re.sub(r"\s+(?:and|then)\s+(?:post|publish|share|send|schedule|email)\b.*$", "", topic, flags=re.I)
    return {
        "scores": scores,
        "city": city, "country": default_country if city == default_city else "", "city_explicit": bool(places_found or route),
        "origin": route.group(1) if route else default_city, "destination": route.group(2) if route else (places_found[0] if places_found else ""),
        "cuisines": find(goal, CUISINES), "diets": find(goal, DIETS), "genres": find(goal, GENRES), "sport": sport, "team": team.group(1).strip() if team else "",
        "amenity": next((a for a, words in AMENITIES.items() if find(goal, words)), "restaurant"),
        "when": when(goal), "budget": {"currency": budget.group(1), "amount": int(budget.group(2).replace(",", "")) * (1000 if budget.group(3) else 1)} if budget and budget.group(2).replace(",", "").isdigit() else {},
        "platforms": [p for p, words in PLATFORMS.items() if any(w in low for w in words)],
        "topic": topic, "wants_movies": bool(find(goal, ("movie", "movies", "film", "films", "cinema"))), "wants_shows": bool(find(goal, ("series", "tv", "show", "shows"))),
        "wants_music": bool(find(goal, ("music", "song", "songs", "playlist", "album", "listen", "artist", "band"))) or bool(find(goal, GENRES)),
        "wants_events": bool(find(goal, ("concert", "concerts", "gig", "gigs", "festival", "festivals", "live", "event", "events", "theatre", "theater", "comedy", "tickets"))),
        "wants_flights": bool(find(goal, ("flight", "flights", "fly", "flying", "airfare"))), "wants_weather": bool(find(goal, ("weather", "forecast", "rain", "temperature"))),
        "wants_books": bool(find(goal, ("book", "books", "read", "reading", "novel", "novels"))), "wants_art": bool(find(goal, ("art", "artwork", "painting", "paintings", "museum", "museums", "gallery", "exhibition"))),
        "wants_fitness": bool(find(goal, ("run", "running", "cycling", "cycle", "ride", "workout", "fitness", "strava", "hike", "walk"))),
    }


FILLER = set("""a an the and or of to in on for with my me i is are be this that it at from by as please find show get some any want would like can you near nearby around best good great top
new what which who when where how plan make give tell us we our need looking look search suggest recommend recommendations ideas idea options things do go going tonight today tomorrow weekend next
week also then about into up out there here now just really very more most""".split())


def keywords(goal: str, drop: tuple[str, ...] = (), limit: int = 5) -> str:
    words = [w for w in re.findall(r"[A-Za-z][\w'&-]+", goal) if w.lower() not in FILLER and w.lower() not in drop]
    return " ".join(words[:limit])

"""Entertainment discovery: events, sports fixtures, movies, shows, music and artists."""
from __future__ import annotations

import base64
import time
from datetime import date, timedelta

from app.config import cred
from app.providers.base import Gateway, ProviderError
from app.schemas.cards import card

SPORT_LEAGUES = {  # TheSportsDB league identifiers
    "football": [(4328, "English Premier League"), (4335, "Spanish La Liga"), (4480, "UEFA Champions League")],
    "basketball": [(4387, "NBA")],
    "cricket": [],  # fetched by day; league ids vary through the season
}


async def ticketmaster_events(gw: Gateway, query: str, city: str, country: str = "", segment: str = "") -> list[dict]:
    params = {"apikey": cred("TICKETMASTER_API_KEY"), "keyword": query, "city": city, "size": 12, "sort": "date,asc"}
    if country:
        params["countryCode"] = country
    if segment:
        params["classificationName"] = segment
    gw.require("ticketmaster")
    d = await gw.get("ticketmaster", "https://app.ticketmaster.com/discovery/v2/events.json", params=params, capability="events")
    out = []
    for e in d.get("_embedded", {}).get("events", []):
        venue = (e.get("_embedded", {}).get("venues") or [{}])[0]
        price = (e.get("priceRanges") or [{}])[0]
        image = max(e.get("images") or [{}], key=lambda i: i.get("width", 0)).get("url", "")
        cls = (e.get("classifications") or [{}])[0]
        out.append(card("ticketmaster", "event", e.get("name"), e.get("url"), image=image, when=e.get("dates", {}).get("start", {}).get("localDate", ""),
                        where=", ".join(x for x in (venue.get("name"), venue.get("city", {}).get("name")) if x), price=price.get("min"), currency=price.get("currency", ""),
                        availability=e.get("dates", {}).get("status", {}).get("code", ""), tags=[cls.get("segment", {}).get("name"), cls.get("genre", {}).get("name")],
                        time=e.get("dates", {}).get("start", {}).get("localTime"), price_max=price.get("max")))
    return out


async def musicbrainz_events(gw: Gateway, query: str, city: str = "") -> list[dict]:
    """Community-maintained live event records. Historical and upcoming; dates are shown as recorded."""
    q = f'"{query}"' + (f' AND place:"{city}"' if city else "")
    d = await gw.get("musicbrainz", "https://musicbrainz.org/ws/2/event", params={"query": q, "fmt": "json", "limit": 10}, capability="events")
    today = date.today().isoformat()
    out = []
    for e in d.get("events", []):
        begin = e.get("life-span", {}).get("begin", "")
        place = next((r["place"]["name"] for r in e.get("relations", []) if r.get("place")), "")
        out.append(card("musicbrainz", "event", e.get("name"), f"https://musicbrainz.org/event/{e['id']}", when=begin, where=place,
                        availability="upcoming" if begin and begin >= today else "past record", tags=[e.get("type")], time=e.get("time")))
    return sorted(out, key=lambda c: c["availability"] != "upcoming")


def _fixture(e: dict) -> dict:
    return card("thesportsdb", "fixture", e.get("strEvent"), f"https://www.thesportsdb.com/event/{e.get('idEvent')}", image=e.get("strThumb") or e.get("strPoster") or "",
                when=(e.get("strTimestamp") or e.get("dateEvent") or "").replace("T", " ")[:16], where=", ".join(x for x in (e.get("strVenue"), e.get("strCountry")) if x),
                availability=e.get("strStatus") or "Scheduled", tags=[e.get("strSport"), e.get("strLeague")], league=e.get("strLeague"), sport=e.get("strSport"),
                home=e.get("strHomeTeam"), away=e.get("strAwayTeam"), round=e.get("intRound"), season=e.get("strSeason"))


async def sports_fixtures(gw: Gateway, sport: str = "football", team: str = "") -> list[dict]:
    sport = sport.lower()
    base = "https://www.thesportsdb.com/api/v1/json/123/"
    out: list[dict] = []
    if team:
        t = await gw.get("thesportsdb", base + "searchteams.php", params={"t": team}, capability="teams")
        for row in (t.get("teams") or [])[:1]:
            out.append(card("thesportsdb", "team", row.get("strTeam"), f"https://www.thesportsdb.com/team/{row.get('idTeam')}", image=row.get("strBadge") or "",
                            where=", ".join(x for x in (row.get("strStadium"), row.get("strLocation")) if x), summary=row.get("strDescriptionEN") or "",
                            tags=[row.get("strSport"), row.get("strLeague")], founded=row.get("intFormedYear")))
            nxt = await gw.get("thesportsdb", base + "eventsnext.php", params={"id": row.get("idTeam")}, capability="fixtures")
            out += [_fixture(e) for e in (nxt.get("events") or [])[:6]]
        return out
    if sport == "cricket":
        for offset in range(3):
            day = (date.today() + timedelta(days=offset)).isoformat()
            d = await gw.get("thesportsdb", base + "eventsday.php", params={"d": day, "s": "Cricket"}, capability="fixtures")
            out += [_fixture(e) for e in (d.get("events") or [])[:6]]
        return out
    errors = []
    for league_id, _name in SPORT_LEAGUES.get(sport, SPORT_LEAGUES["football"]):
        try:
            d = await gw.get("thesportsdb", base + "eventsnextleague.php", params={"id": league_id}, capability="fixtures")
        except ProviderError as exc:
            errors.append(exc)
            continue
        out += [_fixture(e) for e in (d.get("events") or [])[:5]]
    if not out and errors:
        raise errors[0]
    return out


async def itunes_music(gw: Gateway, query: str, entity: str = "song", country: str = "") -> list[dict]:
    params = {"term": query, "media": "music", "entity": entity, "limit": 12}
    if country:
        params["country"] = country
    d = await gw.get("itunes", "https://itunes.apple.com/search", params=params, capability="music")
    out = []
    for r in d.get("results", []):
        if entity == "musicArtist":
            out.append(card("itunes", "artist", r.get("artistName"), r.get("artistLinkUrl"), tags=[r.get("primaryGenreName")], artist_id=r.get("artistId")))
        else:
            out.append(card("itunes", "track" if entity == "song" else "album", r.get("trackName") or r.get("collectionName"), r.get("trackViewUrl") or r.get("collectionViewUrl"),
                            image=(r.get("artworkUrl100") or "").replace("100x100", "400x400"), summary=f"{r.get('artistName', '')} · {r.get('collectionName', '')}",
                            when=(r.get("releaseDate") or "")[:10], price=r.get("trackPrice") if (r.get("trackPrice") or 0) > 0 else None, currency=r.get("currency", ""),
                            tags=[r.get("primaryGenreName")], artist=r.get("artistName"), preview_url=r.get("previewUrl"), duration_s=round((r.get("trackTimeMillis") or 0) / 1000) or None))
    return out


async def itunes_top_movies(gw: Gateway, country: str = "us", limit: int = 12) -> list[dict]:
    d = await gw.get("itunes", f"https://itunes.apple.com/{country.lower() or 'us'}/rss/topmovies/limit={limit}/json", capability="movies")
    out = []
    for e in d.get("feed", {}).get("entry", []):
        price = e.get("im:price", {}).get("attributes", {})
        link = e.get("link")
        href = (link[0] if isinstance(link, list) else link or {}).get("attributes", {}).get("href", "")
        amount = float(price["amount"]) if price.get("amount") else None
        out.append(card("itunes", "movie", e.get("im:name", {}).get("label"), href, image=(e.get("im:image") or [{}])[-1].get("label", "").replace("113x170", "400x600"),
                        summary=e.get("summary", {}).get("label", ""), when=e.get("im:releaseDate", {}).get("attributes", {}).get("label", ""),
                        price=amount if amount else None, currency=price.get("currency", ""), tags=[e.get("category", {}).get("attributes", {}).get("label")],
                        director=e.get("im:artist", {}).get("label"), chart=f"iTunes top movies ({country.upper()})"))
    return out


async def tmdb_movies(gw: Gateway, query: str = "", trending: bool = False) -> list[dict]:
    gw.require("tmdb")
    headers = {"Authorization": "Bearer " + cred("TMDB_READ_TOKEN")}
    if trending or not query:
        d = await gw.get("tmdb", "https://api.themoviedb.org/3/trending/movie/week", headers=headers, capability="movies")
    else:
        d = await gw.get("tmdb", "https://api.themoviedb.org/3/search/movie", headers=headers, params={"query": query, "include_adult": "false"}, capability="movies")
    return [card("tmdb", "movie", m.get("title"), f"https://www.themoviedb.org/movie/{m['id']}", summary=m.get("overview", ""),
                 image=f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else "", when=m.get("release_date", ""),
                 rating=m.get("vote_average"), votes=m.get("vote_count"), language=m.get("original_language")) for m in d.get("results", [])[:12]]


async def tvmaze_shows(gw: Gateway, query: str) -> list[dict]:
    d = await gw.get("tvmaze", "https://api.tvmaze.com/search/shows", params={"q": query}, capability="shows")
    out = []
    for row in d[:10] if isinstance(d, list) else []:
        s = row.get("show", {})
        out.append(card("tvmaze", "show", s.get("name"), s.get("url"), image=(s.get("image") or {}).get("original", ""), summary=s.get("summary", ""),
                        when=s.get("premiered") or "", rating=(s.get("rating") or {}).get("average"), availability=s.get("status", ""), tags=s.get("genres", []),
                        network=((s.get("network") or s.get("webChannel") or {}).get("name"))))
    return out


async def musicbrainz_artist(gw: Gateway, name: str) -> list[dict]:
    d = await gw.get("musicbrainz", "https://musicbrainz.org/ws/2/artist", params={"query": f'artist:"{name}"', "fmt": "json", "limit": 5}, capability="artists")
    return [card("musicbrainz", "artist", a.get("name"), f"https://musicbrainz.org/artist/{a['id']}", summary=a.get("disambiguation", ""),
                 where=(a.get("area") or {}).get("name", ""), when=(a.get("life-span") or {}).get("begin", ""), tags=[t["name"] for t in sorted(a.get("tags", []), key=lambda t: -t.get("count", 0))[:5]],
                 type=a.get("type"), country=a.get("country"), match_score=a.get("score")) for a in d.get("artists", [])]


_spotify_token: dict = {}


async def _spotify_app_token(gw: Gateway) -> str:
    gw.require("spotify")
    if _spotify_token.get("exp", 0) > time.time() + 30:
        return _spotify_token["value"]
    basic = base64.b64encode(f"{cred('SPOTIFY_CLIENT_ID')}:{cred('SPOTIFY_CLIENT_SECRET')}".encode()).decode()
    d = await gw.post("spotify", "https://accounts.spotify.com/api/token", headers={"Authorization": "Basic " + basic}, data={"grant_type": "client_credentials"}, idempotent=True, cache=False, capability="token")
    _spotify_token.update(value=d["access_token"], exp=time.time() + d.get("expires_in", 3600))
    return d["access_token"]


async def spotify_search(gw: Gateway, query: str, kind: str = "track") -> list[dict]:
    token = await _spotify_app_token(gw)
    d = await gw.get("spotify", "https://api.spotify.com/v1/search", headers={"Authorization": "Bearer " + token}, params={"q": query, "type": kind, "limit": 10}, capability="music")
    out = []
    for t in d.get(kind + "s", {}).get("items", []):
        images = (t.get("album", {}) if kind == "track" else t).get("images") or [{}]
        out.append(card("spotify", kind, t.get("name"), t.get("external_urls", {}).get("spotify"), image=images[0].get("url", ""),
                        summary=", ".join(a["name"] for a in t.get("artists", [])), tags=t.get("genres", [])[:4], uri=t.get("uri"), popularity=t.get("popularity")))
    return out


async def lastfm_similar(gw: Gateway, artist: str) -> list[dict]:
    gw.require("lastfm")
    d = await gw.get("lastfm", "https://ws.audioscrobbler.com/2.0/", params={"method": "artist.getsimilar", "artist": artist, "api_key": cred("LASTFM_API_KEY"), "format": "json", "limit": 8}, capability="artists")
    return [card("lastfm", "artist", a.get("name"), a.get("url"), summary=f"Similar to {artist}", similarity=round(float(a.get("match", 0)), 2)) for a in d.get("similarartists", {}).get("artist", [])]


async def youtube_videos(gw: Gateway, query: str) -> list[dict]:
    gw.require("youtube")
    d = await gw.get("youtube", "https://www.googleapis.com/youtube/v3/search", params={"key": cred("YOUTUBE_API_KEY"), "q": query, "type": "video", "part": "snippet", "maxResults": 8, "safeSearch": "moderate"}, capability="videos")
    return [card("youtube", "video", v["snippet"]["title"], "https://www.youtube.com/watch?v=" + v["id"]["videoId"], image=v["snippet"].get("thumbnails", {}).get("high", {}).get("url", ""),
                 summary=v["snippet"].get("description", ""), when=v["snippet"].get("publishedAt", "")[:10], channel=v["snippet"].get("channelTitle")) for v in d.get("items", [])]

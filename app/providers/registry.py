"""Provider registry: live verification, connection status and usage telemetry.

A provider is reported as connected only after a real probe request succeeded. The presence of an
environment variable alone yields `configured_unverified`.
"""
from __future__ import annotations

import asyncio
import time

from app.config import cred
from app.providers.base import Gateway, ProviderError, ProviderSpec, Status
from app.repositories.db import Database, now

# Lightweight, side-effect-free probe per provider: (method, url, kwargs builder).
PROBES: dict[str, tuple] = {
    "open_meteo": ("GET", "https://geocoding-api.open-meteo.com/v1/search", lambda: {"params": {"name": "Delhi", "count": 1}}),
    "met_norway": ("GET", "https://api.met.no/weatherapi/locationforecast/2.0/status", lambda: {}),
    "nominatim": ("GET", "https://nominatim.openstreetmap.org/status", lambda: {"params": {"format": "json"}}),
    "overpass": ("GET", "https://overpass-api.de/api/interpreter", lambda: {"params": {"data": "[out:json][timeout:5];node(1);out ids;"}}),
    "itunes": ("GET", "https://itunes.apple.com/search", lambda: {"params": {"term": "jazz", "limit": 1}}),
    "musicbrainz": ("GET", "https://musicbrainz.org/ws/2/artist", lambda: {"params": {"query": "artist:queen", "fmt": "json", "limit": 1}}),
    "thesportsdb": ("GET", "https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php", lambda: {"params": {"id": 4328}}),
    "tvmaze": ("GET", "https://api.tvmaze.com/shows/1", lambda: {}),
    "openlibrary": ("GET", "https://openlibrary.org/search.json", lambda: {"params": {"q": "travel", "limit": 1, "fields": "key"}}),
    "artic": ("GET", "https://api.artic.edu/api/v1/artworks/search", lambda: {"params": {"q": "monet", "limit": 1, "fields": "id"}}),
    "met_museum": ("GET", "https://collectionapi.metmuseum.org/public/collection/v1.1/search", lambda: {"params": {"q": "sunflowers", "limit": 1}}),
    "wikipedia": ("GET", "https://en.wikipedia.org/w/rest.php/v1/search/page", lambda: {"params": {"q": "music", "limit": 1}}),
    "wikivoyage": ("GET", "https://en.wikivoyage.org/w/api.php", lambda: {"params": {"action": "query", "meta": "siteinfo", "format": "json"}}),
    "commons": ("GET", "https://commons.wikimedia.org/w/api.php", lambda: {"params": {"action": "query", "meta": "siteinfo", "format": "json"}}),
    "duckduckgo": ("GET", "https://api.duckduckgo.com/", lambda: {"params": {"q": "weather", "format": "json", "no_html": 1}}),
    "ticketmaster": ("GET", "https://app.ticketmaster.com/discovery/v2/events.json", lambda: {"params": {"apikey": cred("TICKETMASTER_API_KEY"), "size": 1}}),
    "tmdb": ("GET", "https://api.themoviedb.org/3/authentication", lambda: {"headers": {"Authorization": "Bearer " + cred("TMDB_READ_TOKEN")}}),
    "youtube": ("GET", "https://www.googleapis.com/youtube/v3/videoCategories", lambda: {"params": {"key": cred("YOUTUBE_API_KEY"), "part": "snippet", "regionCode": "US"}}),
    "lastfm": ("GET", "https://ws.audioscrobbler.com/2.0/", lambda: {"params": {"method": "chart.gettopartists", "api_key": cred("LASTFM_API_KEY"), "format": "json", "limit": 1}}),
    "opentripmap": ("GET", "https://api.opentripmap.com/0.1/en/places/geoname", lambda: {"params": {"name": "Paris", "apikey": cred("OPENTRIPMAP_API_KEY")}}),
    "geonames": ("GET", "https://secure.geonames.org/searchJSON", lambda: {"params": {"q": "delhi", "maxRows": 1, "username": cred("GEONAMES_USERNAME")}}),
    "google_books": ("GET", "https://www.googleapis.com/books/v1/volumes", lambda: {"params": {"q": "travel", "maxResults": 1, "key": cred("GOOGLE_BOOKS_KEY")}}),
    "strava": ("GET", "https://www.strava.com/api/v3/athlete", lambda: {"headers": {"Authorization": "Bearer " + cred("STRAVA_ACCESS_TOKEN")}}),
    "google_calendar_read": ("GET", "https://www.googleapis.com/calendar/v3/users/me/calendarList", lambda: {"params": {"maxResults": 1}, "headers": {"Authorization": "Bearer " + cred("GOOGLE_CALENDAR_ACCESS_TOKEN")}}),
    "google_calendar": ("GET", "https://www.googleapis.com/calendar/v3/users/me/calendarList", lambda: {"params": {"maxResults": 1}, "headers": {"Authorization": "Bearer " + cred("GOOGLE_CALENDAR_ACCESS_TOKEN")}}),
    "google_tasks": ("GET", "https://tasks.googleapis.com/tasks/v1/users/@me/lists", lambda: {"params": {"maxResults": 1}, "headers": {"Authorization": "Bearer " + cred("GOOGLE_TASKS_ACCESS_TOKEN")}}),
    "google_drive": ("GET", "https://www.googleapis.com/drive/v3/about", lambda: {"params": {"fields": "user"}, "headers": {"Authorization": "Bearer " + cred("GOOGLE_DRIVE_ACCESS_TOKEN")}}),
    "gmail": ("GET", "https://gmail.googleapis.com/gmail/v1/users/me/profile", lambda: {"headers": {"Authorization": "Bearer " + cred("GMAIL_ACCESS_TOKEN")}}),
    "x": ("GET", "https://api.x.com/2/users/me", lambda: {"headers": {"Authorization": "Bearer " + cred("X_USER_ACCESS_TOKEN")}}),
    "linkedin": ("GET", "https://api.linkedin.com/v2/userinfo", lambda: {"headers": {"Authorization": "Bearer " + cred("LINKEDIN_ACCESS_TOKEN")}}),
    "telegram": ("GET", "https://api.telegram.org/bot" + "{TELEGRAM_BOT_TOKEN}" + "/getMe", lambda: {}),
    "slack": ("POST", "https://slack.com/api/auth.test", lambda: {"headers": {"Authorization": "Bearer " + cred("SLACK_BOT_TOKEN")}, "idempotent": True}),
    "notion": ("GET", "https://api.notion.com/v1/users/me", lambda: {"headers": {"Authorization": "Bearer " + cred("NOTION_TOKEN"), "Notion-Version": "2022-06-28"}}),
    "todoist": ("GET", "https://api.todoist.com/api/v1/projects", lambda: {"headers": {"Authorization": "Bearer " + cred("TODOIST_API_TOKEN")}}),
    "ms_graph": ("GET", "https://graph.microsoft.com/v1.0/me", lambda: {"headers": {"Authorization": "Bearer " + cred("MS_GRAPH_ACCESS_TOKEN")}}),
    "spotify_playlist": ("GET", "https://api.spotify.com/v1/me", lambda: {"headers": {"Authorization": "Bearer " + cred("SPOTIFY_USER_ACCESS_TOKEN")}}),
    "openai": ("GET", "https://api.openai.com/v1/models", lambda: {"headers": {"Authorization": "Bearer " + cred("OPENAI_API_KEY")}}),
    "anthropic": ("GET", "https://api.anthropic.com/v1/models", lambda: {"headers": {"x-api-key": cred("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"}}),
    "gemini": ("GET", "https://generativelanguage.googleapis.com/v1beta/models", lambda: {"headers": {"x-goog-api-key": cred("GEMINI_API_KEY")}}),
    "openrouter": ("GET", "https://openrouter.ai/api/v1/key", lambda: {"headers": {"Authorization": "Bearer " + cred("OPENROUTER_API_KEY")}}),
    "groq": ("GET", "https://api.groq.com/openai/v1/models", lambda: {"headers": {"Authorization": "Bearer " + cred("GROQ_API_KEY")}}),
}

ERROR_STATUS = {"auth": Status.AUTH_EXPIRED, "rate_limit": Status.RATE_LIMITED, "config": Status.CONFIG_REQUIRED}


class Registry:
    def __init__(self, gateway: Gateway, db: Database):
        self.gw, self.db, self.specs = gateway, db, gateway.specs

    async def verify(self, provider: str) -> dict:
        spec = self.specs[provider]
        if spec.access == "handoff":
            return self.describe(spec)
        if not spec.configured:
            self._save(provider, False, "config", "Credentials are not configured", 0)
            return self.describe(spec)
        probe = PROBES.get(provider)
        if probe is None:
            # No safe read-only probe exists for this adapter; it stays configured-but-unverified until first use.
            self.db.run("DELETE FROM provider_checks WHERE provider=?", (provider,))
            return self.describe(spec)
        method, url, build = probe
        if provider == "telegram":
            url = url.replace("{TELEGRAM_BOT_TOKEN}", cred("TELEGRAM_BOT_TOKEN"))
        started = time.monotonic()
        try:
            data = await self.gw.request(provider, method, url, capability="verify", cache=False, **build())
            if provider == "slack" and isinstance(data, dict) and not data.get("ok"):
                raise ProviderError(provider, "auth", "Slack rejected the token")
            self._save(provider, True, "", "Probe succeeded", (time.monotonic() - started) * 1000)
        except ProviderError as exc:
            self._save(provider, False, exc.kind, str(exc), (time.monotonic() - started) * 1000)
        except ValueError as exc:
            self._save(provider, False, "config", str(exc), 0)
        return self.describe(spec)

    async def verify_all(self, only_configured: bool = True) -> list[dict]:
        targets = [p for p, s in self.specs.items() if s.access != "handoff" and (s.configured or not only_configured)]
        await asyncio.gather(*(self.verify(p) for p in targets))
        return self.list()

    def _save(self, provider, ok, kind, detail, latency):
        self.db.run("INSERT OR REPLACE INTO provider_checks VALUES(?,?,?,?,?,?)", (provider, int(ok), kind, detail[:300], round(latency, 1), now()))

    def status(self, spec: ProviderSpec, check: dict | None) -> Status:
        if spec.access == "handoff":
            return Status.HANDOFF
        if not spec.configured:
            return Status.CONFIG_REQUIRED
        st = self.gw._states.get(spec.id)
        if st and st.breaker.open:
            return Status.UNAVAILABLE
        if st and st.last_error in ERROR_STATUS and (not check or st.last_error_at > check["checked"]):
            return ERROR_STATUS[st.last_error]
        if not check:
            return Status.UNVERIFIED
        if check["ok"]:
            return Status.CONNECTED
        return ERROR_STATUS.get(check["error_class"], Status.UNAVAILABLE)

    def describe(self, spec: ProviderSpec) -> dict:
        check = self.db.one("SELECT * FROM provider_checks WHERE provider=?", (spec.id,))
        usage = self.db.one(
            "SELECT COUNT(*) calls, COALESCE(SUM(ok),0) ok, COALESCE(SUM(cached),0) cached, COALESCE(SUM(retries),0) retries, AVG(CASE WHEN cached=0 THEN latency_ms END) latency FROM provider_calls WHERE provider=? AND capability!='verify'",
            (spec.id,),
        )
        status = self.status(spec, check)
        return {
            "id": spec.id, "name": spec.name, "category": spec.category, "access": spec.access,
            "capabilities": list(spec.capabilities), "auth": {"required": list(spec.env), "missing": [k for k in spec.env if not cred(k)], "scopes": list(spec.scopes)},
            "status": status.value, "detail": (check or {}).get("detail", "") if spec.configured else "", "checked_at": (check or {}).get("checked"),
            "probe_latency_ms": (check or {}).get("latency_ms"), "docs": spec.docs, "homepage": spec.homepage, "attribution": spec.attribution,
            "limits": {"rate_per_min": spec.rate_per_min, "timeout_s": spec.timeout_s, "retries": spec.retries, "concurrency": spec.concurrency, "cache_ttl_s": spec.cache_ttl_s},
            "permissions": {"read": spec.access in ("read", "llm"), "write": spec.access == "write", "approval_required": spec.access == "write"},
            "response_schema": spec.response_schema,
            "usage": {"calls": usage["calls"], "ok": usage["ok"], "errors": usage["calls"] - usage["ok"], "cached": usage["cached"], "retries": usage["retries"], "avg_latency_ms": round(usage["latency"], 1) if usage["latency"] else None},
        }

    def list(self) -> list[dict]:
        return [self.describe(s) for s in self.specs.values()]

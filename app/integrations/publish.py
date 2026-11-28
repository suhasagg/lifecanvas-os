"""Authenticated write adapters. Only the Action execution graph may call these, and only for approved actions.

Each adapter validates its payload, sends exactly one request (no retries) and returns a provider receipt.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import quote, urlsplit

from app.config import cred
from app.providers.base import Gateway, ProviderError
from app.security import EMAIL_RE, assert_public_https

LIMITS = {"x": 280, "bluesky": 300, "mastodon": 500, "linkedin": 3000, "instagram": 2200, "facebook": 5000, "telegram": 4096, "discord": 2000, "slack": 4000}
SOCIAL = tuple(LIMITS)
EXTERNAL = (*SOCIAL, "wordpress", "gmail", "google_calendar", "google_tasks", "google_drive", "notion", "todoist", "ms_graph", "spotify_playlist", "amadeus_flight_order")


def _text(p: dict, key: str, limit: int, required: bool = True) -> str:
    v = p.get(key, "")
    if not isinstance(v, str) or (required and not v.strip()) or len(v) > limit:
        raise ValueError(f"'{key}' must be text of at most {limit} characters")
    return v.strip()


def _when(p: dict, key: str) -> str:
    try:
        d = datetime.fromisoformat(str(p.get(key, "")).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"'{key}' must be an ISO-8601 date-time") from None
    if d.tzinfo is None:
        raise ValueError(f"'{key}' must include a timezone offset")
    return d.isoformat()


def validate(kind: str, p: dict) -> dict:
    """Return the exact, normalised payload that will be sent. Raises ValueError for anything ambiguous."""
    if not isinstance(p, dict):
        raise ValueError("Payload must be an object")
    if kind in SOCIAL:
        out = {"text": _text(p, "text", LIMITS[kind])}
        if kind == "instagram":
            out["image_url"] = assert_public_https(_text(p, "image_url", 800))
        if kind == "slack":
            out["channel"] = _text(p, "channel", 40)
            if not re.fullmatch(r"[CGD][A-Z0-9]{5,39}", out["channel"]):
                raise ValueError("Slack channel must be an explicit channel ID")
        return out
    if kind == "wordpress":
        status = p.get("status", "draft")
        if status not in ("draft", "publish"):
            raise ValueError("WordPress status must be draft or publish")
        return {"title": _text(p, "title", 200), "text": _text(p, "text", 40000), "status": status}
    if kind == "gmail":
        to = _text(p, "to", 254)
        if not EMAIL_RE.fullmatch(to):
            raise ValueError("A single explicit recipient email is required")
        return {"to": to, "subject": _text(p, "subject", 200), "text": _text(p, "text", 10000)}
    if kind == "google_calendar":
        start, end = _when(p, "start"), _when(p, "end")
        if end <= start:
            raise ValueError("Event end must follow its start")
        return {"title": _text(p, "title", 200), "start": start, "end": end, "location": _text(p, "location", 300, False), "description": _text(p, "description", 2000, False)}
    if kind in ("google_tasks", "todoist", "ms_graph"):
        return {"title": _text(p, "title", 200), "notes": _text(p, "notes", 4000, False)}
    if kind == "google_drive":
        return {"title": _text(p, "title", 200), "text": _text(p, "text", 100000)}
    if kind == "notion":
        page = _text(p, "page_id", 36)
        if not re.fullmatch(r"[a-fA-F0-9-]{32,36}", page):
            raise ValueError("An explicit Notion page ID is required")
        return {"page_id": page, "text": _text(p, "text", 1900)}
    if kind == "spotify_playlist":
        tracks = p.get("tracks", [])
        if not isinstance(tracks, list) or len(tracks) > 50 or any(not isinstance(t, str) or len(t) > 200 for t in tracks):
            raise ValueError("'tracks' must be a list of up to 50 names")
        return {"name": _text(p, "name", 100), "description": _text(p, "description", 300, False), "tracks": tracks}
    if kind == "amadeus_flight_order":
        offer, travelers = p.get("offer"), p.get("travelers")
        if not isinstance(offer, dict) or not isinstance(offer.get("price"), dict) or not isinstance(travelers, list) or not 1 <= len(travelers) <= 9:
            raise ValueError("A priced Amadeus flight offer and 1-9 travellers are required")
        try:
            total, cap = float(offer["price"].get("grandTotal") or offer["price"]["total"]), float(p["max_total"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("'max_total' (your spending cap) and the offer price are required") from None
        currency = _text(p, "currency", 3).upper()
        if offer["price"].get("currency") != currency:
            raise ValueError("Offer currency differs from the approved currency")
        if total > cap:
            raise ValueError(f"Fare {total:.2f} {currency} exceeds your cap of {cap:.2f} {currency}")
        for t in travelers:
            if not isinstance(t, dict) or not t.get("name") or not t.get("dateOfBirth") or not t.get("contact"):
                raise ValueError("Each traveller needs name, dateOfBirth and contact, in the Amadeus traveller format")
        return {"offer": offer, "travelers": travelers, "max_total": cap, "currency": currency, "total": total}
    raise ValueError(f"Unsupported action kind: {kind}")


def _base(env: str) -> str:
    value = cred(env).rstrip("/")
    u = urlsplit(value)
    if u.query or u.fragment:
        raise ProviderError(env, "config", f"{env} must be a plain HTTPS base URL")
    try:
        return assert_public_https(value, resolve=True)
    except ValueError as exc:
        raise ProviderError(env, "config", f"{env}: {exc}") from None


async def execute(gw: Gateway, kind: str, p: dict, idempotency_key: str) -> dict:
    """Send one approved action. Returns {'receipt', 'url'}. Raises ProviderError; `sent=True` means outcome unknown."""
    gw.require(kind)
    bearer = lambda env: {"Authorization": "Bearer " + cred(env)}
    post = lambda url, **kw: gw.request(kind, "POST", url, capability="write", cache=False, **kw)
    receipt, link = None, ""
    if kind == "x":
        d = await post("https://api.x.com/2/tweets", headers=bearer("X_USER_ACCESS_TOKEN"), json={"text": p["text"]})
        receipt = d.get("data", {}).get("id")
        link = f"https://x.com/i/web/status/{receipt}" if receipt else ""
    elif kind == "linkedin":
        r = await post("https://api.linkedin.com/rest/posts", expect="raw", headers={**bearer("LINKEDIN_ACCESS_TOKEN"), "LinkedIn-Version": cred("LINKEDIN_VERSION") or "202506", "X-Restli-Protocol-Version": "2.0.0"},
                       json={"author": cred("LINKEDIN_AUTHOR_URN"), "commentary": p["text"], "visibility": "PUBLIC", "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False,
                             "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []}})
        receipt = r.headers.get("x-restli-id")
        link = f"https://www.linkedin.com/feed/update/{receipt}" if receipt else ""
    elif kind in ("instagram", "facebook"):
        version = quote(cred("META_GRAPH_VERSION") or "v23.0", safe="")
        if kind == "facebook":
            d = await post(f"https://graph.facebook.com/{version}/{quote(cred('FACEBOOK_PAGE_ID'), safe='')}/feed", headers=bearer("FACEBOOK_PAGE_TOKEN"), data={"message": p["text"]})
            receipt = d.get("id")
        else:
            base = f"https://graph.facebook.com/{version}/{quote(cred('INSTAGRAM_USER_ID'), safe='')}"
            c = await post(base + "/media", headers=bearer("INSTAGRAM_ACCESS_TOKEN"), data={"image_url": p["image_url"], "caption": p["text"]})
            if not c.get("id"):
                raise ProviderError(kind, "bad_response", "Instagram returned no media container")
            d = await post(base + "/media_publish", headers=bearer("INSTAGRAM_ACCESS_TOKEN"), data={"creation_id": c["id"]})
            receipt = d.get("id")
    elif kind == "bluesky":
        s = await post("https://bsky.social/xrpc/com.atproto.server.createSession", json={"identifier": cred("BLUESKY_HANDLE"), "password": cred("BLUESKY_APP_PASSWORD")})
        d = await post("https://bsky.social/xrpc/com.atproto.repo.createRecord", headers={"Authorization": "Bearer " + s["accessJwt"]},
                       json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": {"$type": "app.bsky.feed.post", "text": p["text"], "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}})
        receipt = d.get("uri")
        link = f"https://bsky.app/profile/{s['did']}/post/{receipt.rsplit('/', 1)[-1]}" if receipt else ""
    elif kind == "mastodon":
        d = await post(_base("MASTODON_BASE_URL") + "/api/v1/statuses", headers={**bearer("MASTODON_ACCESS_TOKEN"), "Idempotency-Key": idempotency_key}, json={"status": p["text"], "visibility": "public"})
        receipt, link = d.get("id"), d.get("url", "")
    elif kind == "wordpress":
        basic = base64.b64encode(f"{cred('WORDPRESS_USER')}:{cred('WORDPRESS_APP_PASSWORD')}".encode()).decode()
        d = await post(_base("WORDPRESS_BASE_URL") + "/wp-json/wp/v2/posts", headers={"Authorization": "Basic " + basic}, json={"title": p["title"], "content": p["text"], "status": p["status"]})
        receipt, link = d.get("id"), d.get("link", "")
    elif kind == "telegram":
        d = await post(f"https://api.telegram.org/bot{cred('TELEGRAM_BOT_TOKEN')}/sendMessage", json={"chat_id": cred("TELEGRAM_CHAT_ID"), "text": p["text"]})
        receipt = d.get("result", {}).get("message_id")
    elif kind == "discord":
        hook = assert_public_https(cred("DISCORD_WEBHOOK_URL"), ("discord.com",))
        d = await post(hook + "?wait=true", json={"content": p["text"], "allowed_mentions": {"parse": []}})
        receipt = d.get("id")
    elif kind == "slack":
        d = await post("https://slack.com/api/chat.postMessage", headers=bearer("SLACK_BOT_TOKEN"), json={"channel": p["channel"], "text": p["text"], "mrkdwn": False})
        if not d.get("ok"):
            raise ProviderError(kind, "auth" if "auth" in str(d.get("error")) else "bad_response", f"Slack rejected the message: {d.get('error')}")
        receipt = d.get("ts")
    elif kind == "gmail":
        m = EmailMessage()
        m["To"], m["Subject"] = p["to"], p["subject"]
        m.set_content(p["text"])
        d = await post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", headers=bearer("GMAIL_ACCESS_TOKEN"), json={"raw": base64.urlsafe_b64encode(m.as_bytes()).decode()})
        receipt = d.get("id")
    elif kind == "google_calendar":
        body = {"summary": p["title"], "start": {"dateTime": p["start"]}, "end": {"dateTime": p["end"]}, "location": p.get("location", ""), "description": p.get("description", "")}
        d = await post("https://www.googleapis.com/calendar/v3/calendars/primary/events", headers=bearer("GOOGLE_CALENDAR_ACCESS_TOKEN"), json=body)
        receipt, link = d.get("id"), d.get("htmlLink", "")
    elif kind == "google_tasks":
        d = await post("https://tasks.googleapis.com/tasks/v1/lists/@default/tasks", headers=bearer("GOOGLE_TASKS_ACCESS_TOKEN"), json={"title": p["title"], "notes": p.get("notes", "")})
        receipt = d.get("id")
    elif kind == "google_drive":
        boundary = "lifecanvas" + idempotency_key[:16]
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n" + json.dumps({"name": p["title"], "mimeType": "application/vnd.google-apps.document"})
                + f"\r\n--{boundary}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n{p['text']}\r\n--{boundary}--")
        d = await post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink", content=body.encode(),
                       headers={**bearer("GOOGLE_DRIVE_ACCESS_TOKEN"), "Content-Type": f"multipart/related; boundary={boundary}"})
        receipt, link = d.get("id"), d.get("webViewLink", "")
    elif kind == "notion":
        d = await gw.request(kind, "PATCH", f"https://api.notion.com/v1/blocks/{p['page_id']}/children", capability="write", cache=False,
                             headers={**bearer("NOTION_TOKEN"), "Notion-Version": "2022-06-28"},
                             json={"children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": p["text"]}}]}}]})
        receipt = (d.get("results") or [{}])[0].get("id")
    elif kind == "todoist":
        d = await post("https://api.todoist.com/api/v1/tasks", headers={**bearer("TODOIST_API_TOKEN"), "X-Request-Id": idempotency_key[:36]}, json={"content": p["title"], "description": p.get("notes", "")})
        receipt = d.get("id")
    elif kind == "ms_graph":
        lists = await gw.get(kind, "https://graph.microsoft.com/v1.0/me/todo/lists", headers=bearer("MS_GRAPH_ACCESS_TOKEN"), cache=False, capability="write")
        target = next((x for x in lists.get("value", []) if x.get("wellknownListName") == "defaultList"), None) or (lists.get("value") or [None])[0]
        if not target:
            raise ProviderError(kind, "bad_response", "No Microsoft To Do list is available")
        d = await post(f"https://graph.microsoft.com/v1.0/me/todo/lists/{target['id']}/tasks", headers=bearer("MS_GRAPH_ACCESS_TOKEN"), json={"title": p["title"], "body": {"content": p.get("notes", ""), "contentType": "text"}})
        receipt = d.get("id")
    elif kind == "spotify_playlist":
        d = await post("https://api.spotify.com/v1/me/playlists", headers=bearer("SPOTIFY_USER_ACCESS_TOKEN"), json={"name": p["name"], "description": p.get("description", ""), "public": False})
        receipt, link = d.get("id"), d.get("external_urls", {}).get("spotify", "")
        uris = []
        for name in p.get("tracks", [])[:50]:
            s = await gw.get(kind, "https://api.spotify.com/v1/search", headers=bearer("SPOTIFY_USER_ACCESS_TOKEN"), params={"q": name, "type": "track", "limit": 1}, capability="write")
            uris += [t["uri"] for t in s.get("tracks", {}).get("items", [])[:1]]
        if receipt and uris:
            await post(f"https://api.spotify.com/v1/playlists/{receipt}/tracks", headers=bearer("SPOTIFY_USER_ACCESS_TOKEN"), json={"uris": uris})
    elif kind == "amadeus_flight_order":
        import os
        base = "https://api.amadeus.com" if os.getenv("AMADEUS_ENV") == "production" else "https://test.api.amadeus.com"
        t = await post(base + "/v1/security/oauth2/token", data={"grant_type": "client_credentials", "client_id": cred("AMADEUS_CLIENT_ID"), "client_secret": cred("AMADEUS_CLIENT_SECRET")})
        d = await post(base + "/v1/booking/flight-orders", headers={"Authorization": "Bearer " + t["access_token"]}, json={"data": {"type": "flight-order", "flightOffers": [p["offer"]], "travelers": p["travelers"]}})
        receipt = d.get("data", {}).get("id")
    if not receipt:
        raise ProviderError(kind, "bad_response", "The provider accepted the request but returned no receipt; verify in the app before retrying", sent=True)
    return {"receipt": str(receipt), "url": link}

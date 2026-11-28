"""Research sources: Tavily web search (credentialed), Wikipedia, DuckDuckGo Instant Answers, Wikimedia Commons."""
from __future__ import annotations

from urllib.parse import quote

from app.config import cred
from app.providers.base import Gateway
from app.schemas.cards import card


async def tavily_search(gw: Gateway, query: str, deep: bool = False) -> list[dict]:
    gw.require("tavily")
    d = await gw.post("tavily", "https://api.tavily.com/search", idempotent=True, capability="web_search", headers={"Authorization": "Bearer " + cred("TAVILY_API_KEY")},
                      json={"query": query, "max_results": 8 if deep else 5, "search_depth": "advanced" if deep else "basic", "include_answer": False})
    return [card("tavily", "source", r.get("title"), r.get("url"), summary=r.get("content", ""), when=r.get("published_date", ""), relevance=r.get("score")) for r in d.get("results", [])]


async def wikipedia_search(gw: Gateway, query: str, limit: int = 6) -> list[dict]:
    d = await gw.get("wikipedia", "https://en.wikipedia.org/w/rest.php/v1/search/page", params={"q": query, "limit": limit}, capability="search")
    out = []
    for p in d.get("pages", []):
        thumb = (p.get("thumbnail") or {}).get("url", "")
        out.append(card("wikipedia", "source", p.get("title"), "https://en.wikipedia.org/wiki/" + quote(p.get("key", "")), summary=p.get("description") or p.get("excerpt", ""),
                        image=("https:" + thumb) if thumb.startswith("//") else thumb, excerpt=p.get("excerpt", "")))
    return out


async def wikipedia_summary(gw: Gateway, title: str) -> list[dict]:
    d = await gw.get("wikipedia", "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"), safe=""), capability="summary")
    if d.get("type") == "disambiguation" or not d.get("extract"):
        return []
    return [card("wikipedia", "source", d.get("title"), d.get("content_urls", {}).get("desktop", {}).get("page"), summary=d.get("extract", ""),
                 image=(d.get("thumbnail") or {}).get("source", ""), description=d.get("description"), last_edited=d.get("timestamp"))]


async def instant_answer(gw: Gateway, query: str) -> list[dict]:
    d = await gw.get("duckduckgo", "https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}, capability="answers")
    out = []
    if d.get("AbstractText") and d.get("AbstractURL"):
        out.append(card("duckduckgo", "source", d.get("Heading") or query, d["AbstractURL"], summary=d["AbstractText"], image=("https://duckduckgo.com" + d["Image"]) if d.get("Image", "").startswith("/") else "", origin=d.get("AbstractSource")))
    for t in d.get("RelatedTopics", [])[:5]:
        if t.get("FirstURL") and t.get("Text"):
            out.append(card("duckduckgo", "source", t["Text"].split(" - ")[0][:120], t["FirstURL"], summary=t["Text"]))
    return out


async def commons_images(gw: Gateway, query: str, limit: int = 6) -> list[dict]:
    d = await gw.get("commons", "https://commons.wikimedia.org/w/api.php", capability="images", params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 640})
    out = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        out.append(card("commons", "image", p.get("title", "").removeprefix("File:"), info.get("descriptionurl"), image=info.get("thumburl", ""),
                        summary=meta.get("ImageDescription", {}).get("value", ""), license=meta.get("LicenseShortName", {}).get("value"), artist=meta.get("Artist", {}).get("value")))
    return out

"""Normalised result card. Every provider result carries attribution, source URL and retrieval time."""
from __future__ import annotations

from datetime import datetime, timezone

from app.providers.catalog import ALL
from app.security import clean_text, safe_url


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def card(provider: str, kind: str, title, url="", *, summary="", image="", when="", where="", price=None, currency="",
         availability="", rating=None, tags=(), **meta) -> dict:
    spec = ALL.get(provider)
    return {
        "provider": spec.name if spec else provider,
        "provider_id": provider,
        "attribution": spec.attribution if spec else "",
        "kind": kind,
        "title": clean_text(title, 160) or "Untitled",
        "url": safe_url(url),
        "summary": clean_text(summary, 480),
        "image": safe_url(image),
        "when": clean_text(when, 60),
        "where": clean_text(where, 160),
        "price": price if isinstance(price, (int, float)) else None,
        "currency": clean_text(currency, 6),
        "availability": clean_text(availability, 60),
        "rating": rating if isinstance(rating, (int, float)) else None,
        "tags": [clean_text(t, 32) for t in tags if t][:8],
        "meta": {k: (clean_text(v, 200) if isinstance(v, str) else v) for k, v in meta.items() if v not in (None, "", [], {})},
        "retrieved_at": utcnow(),
    }

"""Culture and wellness: books, artworks, museum collections and authorised fitness summaries."""
from __future__ import annotations

import asyncio

from app.config import cred
from app.providers.base import Gateway, ProviderError
from app.schemas.cards import card


async def books(gw: Gateway, query: str) -> list[dict]:
    d = await gw.get("openlibrary", "https://openlibrary.org/search.json", capability="books",
                     params={"q": query, "limit": 12, "fields": "key,title,author_name,first_publish_year,cover_i,subject,ratings_average,edition_count"})
    return [card("openlibrary", "book", b.get("title"), "https://openlibrary.org" + b["key"], summary=", ".join(b.get("author_name", [])[:3]),
                 image=f"https://covers.openlibrary.org/b/id/{b['cover_i']}-L.jpg" if b.get("cover_i") else "", when=str(b.get("first_publish_year") or ""),
                 rating=round(b["ratings_average"], 1) if b.get("ratings_average") else None, tags=(b.get("subject") or [])[:3], editions=b.get("edition_count"))
            for b in d.get("docs", []) if b.get("key", "").startswith("/works/")]


async def google_books(gw: Gateway, query: str) -> list[dict]:
    gw.require("google_books")
    d = await gw.get("google_books", "https://www.googleapis.com/books/v1/volumes", params={"q": query, "maxResults": 10, "key": cred("GOOGLE_BOOKS_KEY")}, capability="books")
    out = []
    for v in d.get("items", []):
        i, sale = v.get("volumeInfo", {}), v.get("saleInfo", {})
        price = sale.get("retailPrice", {})
        out.append(card("google_books", "book", i.get("title"), i.get("infoLink"), summary=", ".join(i.get("authors", [])), image=(i.get("imageLinks", {}).get("thumbnail") or "").replace("http://", "https://"),
                        when=i.get("publishedDate", ""), rating=i.get("averageRating"), price=price.get("amount"), currency=price.get("currencyCode", ""), availability=sale.get("saleability", "").replace("_", " ").title(),
                        tags=i.get("categories", [])[:3]))
    return out


async def artworks(gw: Gateway, query: str) -> list[dict]:
    d = await gw.get("artic", "https://api.artic.edu/api/v1/artworks/search", capability="artworks",
                     params={"q": query, "limit": 8, "fields": "id,title,artist_display,date_display,image_id,medium_display,is_public_domain,place_of_origin"})
    iiif = d.get("config", {}).get("iiif_url", "https://www.artic.edu/iiif/2")
    return [card("artic", "artwork", a.get("title"), f"https://www.artic.edu/artworks/{a['id']}", summary=a.get("artist_display", ""), when=a.get("date_display", ""),
                 image=f"{iiif}/{a['image_id']}/full/600,/0/default.jpg" if a.get("image_id") else "", where=a.get("place_of_origin") or "",
                 tags=[a.get("medium_display"), "public domain" if a.get("is_public_domain") else None], museum="Art Institute of Chicago") for a in d.get("data", [])]


async def met_artworks(gw: Gateway, query: str) -> list[dict]:
    d = await gw.get("met_museum", "https://collectionapi.metmuseum.org/public/collection/v1.1/search", params={"q": query, "limit": 8, "hasImages": "true"}, capability="artworks")
    ids = (d.get("objectIDs") or [])[:6]

    async def one(oid):
        try:
            return await gw.get("met_museum", f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}", capability="artworks")
        except ProviderError:
            return None

    out = []
    for o in await asyncio.gather(*(one(i) for i in ids)):
        if o and o.get("title"):
            out.append(card("met_museum", "artwork", o["title"], o.get("objectURL"), summary=o.get("artistDisplayName") or o.get("culture") or "", when=o.get("objectDate", ""),
                            image=o.get("primaryImageSmall", ""), where=o.get("department", ""), tags=[o.get("medium"), "public domain" if o.get("isPublicDomain") else None],
                            museum="The Metropolitan Museum of Art", gallery=o.get("GalleryNumber")))
    return out


async def strava_activities(gw: Gateway) -> list[dict]:
    """The signed-in owner's own recent activities. Requires a user-granted Strava token (activity:read)."""
    gw.require("strava")
    d = await gw.get("strava", "https://www.strava.com/api/v3/athlete/activities", headers={"Authorization": "Bearer " + cred("STRAVA_ACCESS_TOKEN")}, params={"per_page": 10}, cache=False, capability="fitness")
    return [card("strava", "activity", a.get("name"), f"https://www.strava.com/activities/{a['id']}", when=(a.get("start_date_local") or "")[:16].replace("T", " "),
                 summary=f"{a.get('distance', 0) / 1000:.1f} km · {a.get('moving_time', 0) // 60} min · {a.get('total_elevation_gain', 0):.0f} m climb",
                 tags=[a.get("sport_type")], distance_km=round(a.get("distance", 0) / 1000, 2), moving_min=a.get("moving_time", 0) // 60) for a in d if isinstance(d, list)]

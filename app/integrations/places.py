"""Restaurants, cafes and local places: Google Places, Foursquare, OpenStreetMap (Overpass with Nominatim fallback)."""
from __future__ import annotations

from app.config import cred
from app.providers.base import Gateway, ProviderError
from app.schemas.cards import card

OVERPASS_MIRRORS = ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter")
PRICE_LEVELS = {"PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 1, "PRICE_LEVEL_MODERATE": 2, "PRICE_LEVEL_EXPENSIVE": 3, "PRICE_LEVEL_VERY_EXPENSIVE": 4}


def _osm_card(provider: str, tags: dict, lat, lon, osm_type: str, osm_id, amenity: str) -> dict:
    address = ", ".join(x for x in (tags.get("addr:housenumber"), tags.get("addr:street"), tags.get("addr:suburb"), tags.get("addr:city")) if x)
    diet = [k.split(":")[1] for k, v in tags.items() if k.startswith("diet:") and v in ("yes", "only")]
    return card(provider, "place", tags.get("name") or tags.get("name:en"), f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                where=address, summary=" · ".join(x for x in (tags.get("cuisine", "").replace(";", ", ").replace("_", " "), tags.get("opening_hours")) if x),
                tags=[amenity, *tags.get("cuisine", "").split(";")[:3]], cuisine=tags.get("cuisine", "").replace(";", ", "), opening_hours=tags.get("opening_hours"),
                website=tags.get("website") or tags.get("contact:website"), diet=diet, amenity=amenity, lat=float(lat), lon=float(lon),
                outdoor_seating=tags.get("outdoor_seating"), wheelchair=tags.get("wheelchair"), start_date=tags.get("start_date") or tags.get("opening_date"))


async def osm_places(gw: Gateway, lat: float, lon: float, amenity: str = "restaurant", cuisine: str = "", radius_m: int = 3000, area_name: str = "") -> list[dict]:
    """Query OpenStreetMap. Overpass mirrors are tried first; Nominatim is the documented fallback."""
    flt = f'["amenity"="{amenity}"]["name"]' + (f'["cuisine"~"{cuisine}",i]' if cuisine else "")
    query = f"[out:json][timeout:4];nwr{flt}(around:{radius_m},{lat},{lon});out center tags 40;"
    last: ProviderError | None = None
    for mirror in OVERPASS_MIRRORS:
        try:
            d = await gw.get("overpass", mirror, params={"data": query}, capability="places")
        except ProviderError as exc:
            last = exc
            if exc.kind == "circuit_open":
                break
            continue
        out = []
        for e in d.get("elements", []):
            pos = e if "lat" in e else e.get("center", {})
            if pos.get("lat") is not None:
                out.append(_osm_card("overpass", e.get("tags", {}), pos["lat"], pos["lon"], e["type"], e["id"], amenity))
        return out
    q = f"{cuisine + ' ' if cuisine else ''}{amenity} in {area_name}" if area_name else f"{cuisine} {amenity}".strip()
    params = {"q": q, "format": "jsonv2", "extratags": 1, "addressdetails": 1, "limit": 30}
    if not area_name:
        d_lat, d_lon = radius_m / 111_000, radius_m / 95_000
        params.update(viewbox=f"{lon - d_lon},{lat + d_lat},{lon + d_lon},{lat - d_lat}", bounded=1)
    try:
        rows = await gw.get("nominatim", "https://nominatim.openstreetmap.org/search", params=params, capability="places")
    except ProviderError as exc:
        raise (last or exc) from None
    out = []
    for r in rows if isinstance(rows, list) else []:
        if r.get("category") != "amenity" or not r.get("name"):
            continue
        a = r.get("address", {})
        tags = {**(r.get("extratags") or {}), "name": r["name"], "addr:street": a.get("road"), "addr:suburb": a.get("suburb") or a.get("neighbourhood"), "addr:city": a.get("city") or a.get("town")}
        out.append(_osm_card("nominatim", tags, r["lat"], r["lon"], r.get("osm_type", "node"), r.get("osm_id"), r.get("type") or amenity))
    return out


async def google_places(gw: Gateway, query: str, city: str) -> list[dict]:
    gw.require("google_places")
    fields = "places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.rating,places.userRatingCount,places.priceLevel,places.primaryTypeDisplayName,places.currentOpeningHours.openNow,places.location,places.websiteUri"
    d = await gw.post("google_places", "https://places.googleapis.com/v1/places:searchText", idempotent=True, capability="places",
                      headers={"X-Goog-Api-Key": cred("GOOGLE_PLACES_KEY"), "X-Goog-FieldMask": fields}, json={"textQuery": f"{query} in {city}", "maxResultCount": 15})
    out = []
    for p in d.get("places", []):
        open_now = p.get("currentOpeningHours", {}).get("openNow")
        out.append(card("google_places", "place", p.get("displayName", {}).get("text"), p.get("googleMapsUri"), where=p.get("formattedAddress", ""), rating=p.get("rating"),
                        availability="" if open_now is None else ("Open now" if open_now else "Closed now"), tags=[p.get("primaryTypeDisplayName", {}).get("text")],
                        price_level=PRICE_LEVELS.get(p.get("priceLevel")), reviews=p.get("userRatingCount"), website=p.get("websiteUri"),
                        lat=p.get("location", {}).get("latitude"), lon=p.get("location", {}).get("longitude")))
    return out


async def foursquare_places(gw: Gateway, query: str, lat: float, lon: float) -> list[dict]:
    gw.require("foursquare")
    d = await gw.get("foursquare", "https://places-api.foursquare.com/places/search", capability="places",
                     headers={"Authorization": "Bearer " + cred("FOURSQUARE_API_KEY"), "X-Places-Api-Version": "2025-06-17"}, params={"query": query, "ll": f"{lat},{lon}", "limit": 15})
    return [card("foursquare", "place", p.get("name"), p.get("link") or p.get("website") or "", where=p.get("location", {}).get("formatted_address", ""), rating=p.get("rating"),
                 tags=[c.get("name") for c in p.get("categories", [])[:3]], price_level=p.get("price"), distance_m=p.get("distance"), lat=p.get("latitude"), lon=p.get("longitude"))
            for p in d.get("results", [])]

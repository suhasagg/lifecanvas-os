"""Travel: Amadeus flight offers, Wikivoyage destination guides, nearby attractions (Wikipedia geosearch, OpenTripMap)."""
from __future__ import annotations

import os
import time

from app.config import cred
from app.providers.base import Gateway
from app.schemas.cards import card

_token: dict = {}
IATA = {"delhi": "DEL", "new delhi": "DEL", "mumbai": "BOM", "bengaluru": "BLR", "bangalore": "BLR", "goa": "GOI", "chennai": "MAA", "kolkata": "CCU", "hyderabad": "HYD",
        "jaipur": "JAI", "pune": "PNQ", "kochi": "COK", "london": "LHR", "paris": "CDG", "new york": "JFK", "dubai": "DXB", "singapore": "SIN", "bangkok": "BKK", "tokyo": "HND",
        "san francisco": "SFO", "los angeles": "LAX", "sydney": "SYD", "amsterdam": "AMS", "berlin": "BER", "rome": "FCO", "barcelona": "BCN", "lisbon": "LIS", "istanbul": "IST",
        "bali": "DPS", "kathmandu": "KTM", "colombo": "CMB", "udaipur": "UDR", "srinagar": "SXR", "leh": "IXL", "varanasi": "VNS", "ahmedabad": "AMD", "chandigarh": "IXC"}


def iata(city: str) -> str | None:
    c = city.strip()
    return c.upper() if len(c) == 3 and c.isalpha() and c.isupper() else IATA.get(c.lower())


async def flight_offers(gw: Gateway, origin: str, destination: str, depart: str, adults: int = 1) -> list[dict]:
    gw.require("amadeus")
    base = "https://api.amadeus.com" if os.getenv("AMADEUS_ENV") == "production" else "https://test.api.amadeus.com"
    if _token.get("exp", 0) < time.time() + 30:
        t = await gw.post("amadeus", base + "/v1/security/oauth2/token", idempotent=True, cache=False, capability="token",
                          data={"grant_type": "client_credentials", "client_id": cred("AMADEUS_CLIENT_ID"), "client_secret": cred("AMADEUS_CLIENT_SECRET")})
        _token.update(value=t["access_token"], exp=time.time() + t.get("expires_in", 1700))
    d = await gw.get("amadeus", base + "/v2/shopping/flight-offers", headers={"Authorization": "Bearer " + _token["value"]}, capability="flights",
                     params={"originLocationCode": origin, "destinationLocationCode": destination, "departureDate": depart, "adults": adults, "max": 8})
    env = "production" if base.endswith("api.amadeus.com") and "test" not in base else "test environment"
    out = []
    for o in d.get("data", []):
        it = o["itineraries"][0]
        segs = it["segments"]
        out.append(card("amadeus", "flight", f"{segs[0]['departure']['iataCode']} → {segs[-1]['arrival']['iataCode']} · {segs[0]['carrierCode']}{segs[0]['number']}",
                        "https://www.google.com/travel/flights?q=" + f"Flights%20from%20{origin}%20to%20{destination}%20on%20{depart}",
                        when=segs[0]["departure"]["at"].replace("T", " ")[:16], price=float(o["price"]["total"]), currency=o["price"]["currency"],
                        availability=f"{o.get('numberOfBookableSeats', '?')} seats ({env})", summary=f"{it.get('duration', '').replace('PT', '').lower()} · {len(segs) - 1} stop(s)",
                        tags=[env], stops=len(segs) - 1, arrival=segs[-1]["arrival"]["at"], carrier=segs[0]["carrierCode"], environment=env, offer=o))
    return out


async def destination_guide(gw: Gateway, destination: str) -> list[dict]:
    d = await gw.get("wikivoyage", "https://en.wikivoyage.org/w/api.php", capability="destinations", params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": destination, "gsrlimit": 4, "prop": "extracts|pageimages|info", "inprop": "url",
        "exintro": 1, "explaintext": 1, "exlimit": 4, "piprop": "thumbnail", "pithumbsize": 640})
    pages = sorted((d.get("query", {}).get("pages") or {}).values(), key=lambda p: p.get("index", 99))
    return [card("wikivoyage", "guide", p.get("title"), p.get("fullurl"), summary=p.get("extract", ""), image=(p.get("thumbnail") or {}).get("source", ""), tags=["destination guide"]) for p in pages]


async def attractions(gw: Gateway, lat: float, lon: float, radius_m: int = 10000) -> list[dict]:
    if cred("OPENTRIPMAP_API_KEY"):
        d = await gw.get("opentripmap", "https://api.opentripmap.com/0.1/en/places/radius", capability="attractions",
                         params={"radius": radius_m, "lon": lon, "lat": lat, "rate": 3, "format": "json", "limit": 12, "apikey": cred("OPENTRIPMAP_API_KEY")})
        return [card("opentripmap", "attraction", p.get("name"), f"https://opentripmap.com/en/card/{p.get('xid')}", tags=(p.get("kinds") or "").split(",")[:3],
                     distance_m=round(p.get("dist", 0)), lat=p.get("point", {}).get("lat"), lon=p.get("point", {}).get("lon")) for p in d if p.get("name")]
    d = await gw.get("wikipedia", "https://en.wikipedia.org/w/api.php", capability="nearby", params={
        "action": "query", "format": "json", "generator": "geosearch", "ggscoord": f"{lat}|{lon}", "ggsradius": min(radius_m, 10000), "ggslimit": 30,
        "prop": "pageimages|description|info|coordinates", "inprop": "url", "piprop": "thumbnail", "pithumbsize": 480})
    pages = [p for p in (d.get("query", {}).get("pages") or {}).values() if p.get("thumbnail")]
    return [card("wikipedia", "attraction", p.get("title"), p.get("fullurl"), summary=p.get("description", ""), image=p["thumbnail"]["source"], tags=["landmark"],
                 lat=(p.get("coordinates") or [{}])[0].get("lat"), lon=(p.get("coordinates") or [{}])[0].get("lon")) for p in pages[:12]]

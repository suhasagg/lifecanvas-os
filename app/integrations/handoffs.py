"""External application handoffs.

These consumer apps expose no public partner API to this project, so LifeCanvasOS opens a pre-filled search in
the app instead of pretending to book. A handoff never implies availability, price or a completed transaction.
"""
from __future__ import annotations

from urllib.parse import quote, quote_plus

from app.schemas.cards import card

BUILDERS = {
    "bookmyshow": lambda q, c: f"https://in.bookmyshow.com/explore/home/{quote(c.lower().replace(' ', '-'))}",
    "district": lambda q, c: f"https://www.district.in/search?q={quote_plus(q)}",
    "zomato": lambda q, c: f"https://www.zomato.com/{quote(c.lower().replace(' ', '-'))}/restaurants?q={quote_plus(q)}",
    "swiggy": lambda q, c: f"https://www.swiggy.com/search?query={quote_plus(q)}",
    "opentable": lambda q, c: f"https://www.opentable.com/s?term={quote_plus(q + ' ' + c)}",
    "google_maps": lambda q, c: f"https://www.google.com/maps/search/?api=1&query={quote_plus(q + ' ' + c)}",
    "airbnb": lambda q, c: f"https://www.airbnb.com/s/{quote(c)}/homes",
    "makemytrip": lambda q, c: "https://www.makemytrip.com/hotels/",
    "booking": lambda q, c: f"https://www.booking.com/searchresults.html?ss={quote_plus(c)}",
    "uber": lambda q, c: f"https://m.uber.com/looking?drop[0]={quote_plus(q + ' ' + c)}",
    "klook": lambda q, c: f"https://www.klook.com/search/result/?query={quote_plus(c)}",
    "getyourguide": lambda q, c: f"https://www.getyourguide.com/s/?q={quote_plus(c)}",
    "tripadvisor": lambda q, c: f"https://www.tripadvisor.com/Search?q={quote_plus(q + ' ' + c)}",
    "google_flights": lambda q, c: f"https://www.google.com/travel/flights?q={quote_plus(q)}",
}
DOMAINS = {
    "entertainment": ("bookmyshow", "district"),
    "dining": ("zomato", "swiggy", "opentable", "google_maps"),
    "travel": ("google_flights", "makemytrip", "booking", "airbnb", "klook", "getyourguide", "tripadvisor", "uber"),
}
NOTE = "Opens the app with your search. Availability, price and booking are confirmed there, not by LifeCanvasOS."


def handoffs(domain: str, query: str, city: str) -> list[dict]:
    return [card(pid, "handoff", "", BUILDERS[pid](query, city), summary=NOTE, availability="External app", tags=[domain], query=query) | {"title": f"Continue in {card(pid, 'x', 'x')['provider']}"}
            for pid in DOMAINS.get(domain, ())]

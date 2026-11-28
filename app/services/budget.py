"""Budget planning over real, provider-supplied prices.

Only prices a provider actually returned are counted. Items without a price are reported separately as
"price to confirm" and are never assigned an amount.
"""
from __future__ import annotations

from itertools import combinations, product

CATEGORY = {"event": "events", "fixture": "events", "movie": "events", "place": "dining", "flight": "trip", "guide": "trip", "attraction": "trip", "book": "culture", "track": "music", "album": "music"}


def plan(cards: list[dict], budget: float, currency: str, per_category: int = 1) -> dict:
    """Pick the best-scoring combination (at most `per_category` per category) whose total is within budget."""
    if budget <= 0:
        raise ValueError("Budget must be greater than zero")
    currency = currency.upper()
    priced, unpriced, other_currency = {}, [], []
    for c in cards:
        cat = CATEGORY.get(c.get("kind"), "other")
        if c.get("price") is None:
            unpriced.append(c)
        elif (c.get("currency") or "").upper() != currency:
            other_currency.append(c)  # no exchange rates are assumed
        elif c["price"] <= budget:
            priced.setdefault(cat, []).append(c)
    # Bounded search: one "pick" (a subset of up to per_category items) per category.
    width = 8 if per_category == 1 else 4
    pools = []
    for items in priced.values():
        top = sorted(items, key=lambda c: (-(c.get("score") or 0), c["price"]))[:width]
        pools.append([s for n in range(per_category + 1) for s in combinations(top, n)])
    best, best_key = [], (-1, -1.0, 0.0)
    for combo in product(*pools) if pools else [()]:
        chosen = [c for pick in combo for c in pick]
        total = sum(c["price"] for c in chosen)
        if total > budget:
            continue
        key = (len({CATEGORY.get(c["kind"], "other") for c in chosen}), sum(c.get("score") or 0 for c in chosen), -total)
        if key > best_key:
            best, best_key = chosen, key
    total = round(sum(c["price"] for c in best), 2)
    return {"budget": budget, "currency": currency, "total": total, "remaining": round(budget - total, 2), "within_budget": total <= budget,
            "selected": [{"title": c["title"], "kind": c["kind"], "category": CATEGORY.get(c["kind"], "other"), "price": c["price"], "currency": currency, "provider": c.get("provider", ""), "url": c.get("url", ""),
                          "booking": "approval" if c["kind"] == "flight" and (c.get("meta") or {}).get("offer") else "provider_checkout"} for c in best],
            "price_to_confirm": [{"title": c["title"], "kind": c["kind"], "provider": c.get("provider", ""), "url": c.get("url", "")} for c in unpriced[:20]],
            "other_currency": [{"title": c["title"], "price": c["price"], "currency": c.get("currency", "")} for c in other_currency[:20]],
            "note": "Totals use only prices supplied by providers. Final prices are confirmed at provider checkout."}

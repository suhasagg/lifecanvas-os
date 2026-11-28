# Budget and booking

LifeCanvasOS helps you choose what fits a budget and books only where a provider offers a real booking API. It never holds card details.

## What can be booked where

| What | How it completes | Why |
| --- | --- | --- |
| Flights | In LifeCanvasOS, through Amadeus Flight Create Orders, after your approval | Amadeus offers a documented order API |
| Event tickets | At the ticketing provider's checkout, opened by link | Ticketing platforms do not expose a public purchase API |
| Restaurant tables | At the restaurant or reservation app, opened by link | Reservation platforms require partner agreements |
| Stays, rides, activities | At the provider, opened by link | Same reason |

A handoff link opens the provider with your search filled in. It does not imply availability, a price or a completed booking.

## Budget planner

In the app: **My plans → Budget planner**. Save results you like, enter a budget and currency, and choose how many picks you want per category.

Rules the planner follows:

1. Only prices returned by a provider are counted. An item without a price is listed under "Price to confirm" and is never given an amount.
2. Items priced in another currency are listed separately. No exchange rate is assumed.
3. Items are grouped into categories: events (events, fixtures, movies), dining, trip (flights, guides, attractions), culture and music.
4. The planner picks up to *N* items per category so that the total stays within the budget. It prefers plans that cover more categories, then higher relevance, then lower total.
5. To stay fast, it considers the eight best-scoring priced items per category for one pick, and the four best for two or three picks.

The result shows the total, what is left, each chosen item with its provider link, and whether the item books by approval (flights with a live offer) or at the provider's checkout.

Final prices are always confirmed by the provider at checkout.

### API

```bash
curl -b jar -H 'X-Requested-With: lifecanvas' -H 'Content-Type: application/json' \
  -d '{"budget": 6000, "currency": "INR", "per_category": 1, "cards": [
        {"title": "Gig A", "kind": "event", "price": 1500, "currency": "INR", "score": 3},
        {"title": "Dinner", "kind": "place", "price": 900, "currency": "INR", "score": 2},
        {"title": "Cafe", "kind": "place", "price": null}]}' \
  http://localhost:8000/api/budget/plan
```

```json
{"budget": 6000, "currency": "INR", "total": 2400, "remaining": 3600, "within_budget": true,
 "selected": [{"title": "Gig A", "category": "events", "price": 1500, "booking": "provider_checkout"},
              {"title": "Dinner", "category": "dining", "price": 900, "booking": "provider_checkout"}],
 "price_to_confirm": [{"title": "Cafe", "kind": "place"}],
 "other_currency": []}
```

Up to 200 cards are read per request and `per_category` is capped at 3.

## Flight booking

Requires `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET`. The test environment is used unless `AMADEUS_ENV=production`.

1. Search flights in **Travel & escapes**. Each flight card carries the Amadeus offer it came from.
2. Propose an `amadeus_flight_order` action with the offer, the travellers and your spending cap.
3. Review the approval in the **Action center**. It shows the fare and your cap.
4. Approve. The order is sent once. The Amadeus order id is stored as the receipt.

```json
{"items": [{"kind": "amadeus_flight_order", "summary": "DEL to BOM, 5 Dec",
  "payload": {"offer": { "...": "the offer object from the flight card (meta.offer)" },
              "travelers": [{"id": "1", "dateOfBirth": "1990-01-01",
                             "name": {"firstName": "ASHA", "lastName": "VERMA"},
                             "contact": {"emailAddress": "asha@example.com"}}],
              "max_total": 6000, "currency": "INR"}}]}
```

Safeguards:

- The order is refused if the payable amount (the offer's `grandTotal`, or `total` when there is no grand total) is above `max_total`.
- The order is refused if the offer currency differs from the currency you approved.
- 1 to 9 travellers, each with a name, date of birth and contact, in the Amadeus traveller format.
- The approval is bound to a digest of the exact payload, is single use and expires (15 minutes by default).
- A write is never retried automatically. If the request may have reached Amadeus but no answer came back, or the run was cancelled mid-send, the action is recorded as `unknown` and you are told to check with the airline before trying again.

## Limits

- There is no traveller-details form in the UI yet; flight orders are proposed through the API and approved in the Action center.
- Flight orders have not been exercised against the live Amadeus service in this repository's test runs; the offline tests cover validation and the spending cap.
- Fare rules, seat selection, baggage and payment options offered by Amadeus beyond the basic order are not modelled.

import pytest
from fastapi.testclient import TestClient

from app.integrations import publish
from app.services import budget
from app.services.social import agent_verdict
from tests.conftest import HEADERS, signup

CARDS = [{"title": "Gig A", "kind": "event", "price": 1500, "currency": "INR", "score": 3}, {"title": "Gig B", "kind": "event", "price": 600, "currency": "INR", "score": 1},
         {"title": "Dinner", "kind": "place", "price": 900, "currency": "INR", "score": 2}, {"title": "Flight", "kind": "flight", "price": 4000, "currency": "INR", "score": 1},
         {"title": "Cafe", "kind": "place", "price": None, "currency": ""}, {"title": "Show", "kind": "event", "price": 20, "currency": "USD"}]


def test_budget_plan_stays_under_budget_and_never_invents_prices():
    p = budget.plan(CARDS, 2500, "inr")
    assert p["total"] <= 2500 and {x["title"] for x in p["selected"]} == {"Gig A", "Dinner"} and p["remaining"] == 100
    assert [x["title"] for x in p["price_to_confirm"]] == ["Cafe"] and [x["title"] for x in p["other_currency"]] == ["Show"]
    p = budget.plan(CARDS, 6000, "INR")
    assert p["total"] == 5500 and len(p["selected"]) == 3  # one per category, best coverage that fits
    assert budget.plan(CARDS, 100, "INR")["selected"] == []
    with pytest.raises(ValueError):
        budget.plan(CARDS, 0, "INR")


def test_flight_order_is_refused_above_the_approved_cap():
    offer = {"id": "1", "price": {"total": "5200.00", "currency": "INR"}}
    traveller = [{"id": "1", "name": {"firstName": "A", "lastName": "B"}, "dateOfBirth": "1990-01-01", "contact": {"emailAddress": "a@b.co"}}]
    ok = publish.validate("amadeus_flight_order", {"offer": offer, "travelers": traveller, "max_total": 6000, "currency": "INR"})
    assert ok["total"] == 5200.0
    for bad in ({"max_total": 5000, "currency": "INR"}, {"max_total": 6000, "currency": "USD"}, {"max_total": 6000, "currency": "INR", "travelers": []}):
        with pytest.raises(ValueError):
            publish.validate("amadeus_flight_order", {"offer": offer, "travelers": traveller} | bad)


def test_agents_disclose_only_a_verdict():
    option = {"cost_per_person": 800, "date": "2026-12-05", "tags": ["jazz"], "diets": ["vegetarian"]}
    assert agent_verdict({"max_budget": 500}, option) == {"accept": False, "rank": 0}
    assert agent_verdict({"max_budget": 2000, "dates": ["2026-12-05"], "interests": ["Jazz"], "diet": "vegetarian"}, option) == {"accept": True, "rank": 2}
    assert agent_verdict({"dates": ["2026-12-06"]}, option)["accept"] is False


def test_meetup_negotiation_video_call_and_privacy(app, client, user):
    profile = lambda name, interests: {"display_name": name, "city": "Delhi", "interests": interests, "discoverable": True, "adult_confirmed": True}
    client.put("/api/community/profile", json=profile("Asha", ["jazz"]))
    options = [{"title": "Jazz club", "date": "2026-12-05", "cost_per_person": 1800, "currency": "INR", "tags": ["jazz"]}, {"title": "Open mic", "date": "2026-12-05", "cost_per_person": 400, "currency": "INR", "tags": ["music"]},
               {"title": "Rooftop dinner", "date": "2026-12-06", "cost_per_person": 900, "currency": "INR", "tags": ["food"]}]
    with TestClient(app, headers=HEADERS) as bob, TestClient(app, headers=HEADERS) as eve:
        signup(bob, "bob@example.com", "Bob")
        signup(eve, "eve@example.com", "Eve")
        bob.put("/api/community/profile", json=profile("Bob", ["jazz", "music"]))
        asha_id = bob.get("/api/community/matches").json()["matches"][0]["user_id"]
        assert bob.post("/api/community/call", json={"user_id": asha_id}).status_code == 400  # not connected yet
        req = bob.post("/api/community/requests", json={"user_id": asha_id}).json()
        client.post(f"/api/community/requests/{req['id']}", json={"accept": True})
        bob_id = client.get("/api/community/connections").json()["connected"][0]["user_id"]
        call = client.post("/api/community/call", json={"user_id": bob_id}).json()
        assert call["url"].startswith("https://meet.jit.si/LifeCanvas-") and call["url"] == bob.post("/api/community/call", json={"user_id": asha_id}).json()["url"]
        assert eve.post("/api/community/call", json={"user_id": asha_id}).status_code == 400
        assert client.post("/api/meetups", json={"title": "x", "options": options, "invitees": ["nobody"]}).status_code == 400
        m = client.post("/api/meetups", json={"title": "Saturday out", "options": options, "invitees": [bob_id], "constraints": {"max_budget": 2000, "dates": ["2026-12-05"], "interests": ["jazz"]}}).json()
        assert m["status"] == "collecting" and m["chosen"] is None
        theirs = bob.get("/api/meetups").json()["meetups"][0]
        assert theirs["my_constraints"] is None and "2000" not in str(theirs)  # Asha's budget is never shown to Bob
        done = bob.post(f"/api/meetups/{m['id']}/constraints", json={"constraints": {"max_budget": 600, "interests": ["music"]}}).json()
        assert done["status"] == "proposed" and done["chosen"]["title"] == "Open mic" and done["video_call"] is None
        assert eve.post(f"/api/meetups/{m['id']}/confirm").status_code == 400
        client.post(f"/api/meetups/{m['id']}/confirm")
        final = bob.post(f"/api/meetups/{m['id']}/confirm").json()
        assert final["status"] == "confirmed" and final["video_call"].startswith("https://meet.jit.si/")
        none = bob.post(f"/api/meetups/{m['id']}/constraints", json={"constraints": {"max_budget": 100}}).json()
        assert none["status"] == "no_agreement" and none["chosen"] is None
        client.post("/api/community/block", json={"user_id": bob_id})
        assert bob.get("/api/meetups").json()["meetups"] == [] and bob.post(f"/api/meetups/{m['id']}/confirm").status_code == 400


def test_budget_endpoint(client, user):
    r = client.post("/api/budget/plan", json={"budget": 2500, "currency": "INR", "cards": CARDS}).json()
    assert r["total"] == 2400 and r["within_budget"]
    assert client.post("/api/budget/plan", json={"budget": 0, "currency": "INR", "cards": CARDS}).status_code == 400


def test_budget_search_is_bounded_and_grand_total_is_capped():
    import time
    cards = [{"title": f"{k}{i}", "kind": k, "price": 10 + i, "currency": "INR", "score": i} for k in ("event", "place", "flight", "book", "track") for i in range(12)]
    start = time.time()
    p = budget.plan(cards, 500, "INR", 3)
    assert time.time() - start < 5 and p["total"] <= 500 and len(p["selected"]) == 15
    offer = {"price": {"total": "900.00", "grandTotal": "1100.00", "currency": "INR"}}
    with pytest.raises(ValueError):
        publish.validate("amadeus_flight_order", {"offer": offer, "travelers": [{"name": {}, "dateOfBirth": "1990-01-01", "contact": {}}], "max_total": 1000, "currency": "INR"})

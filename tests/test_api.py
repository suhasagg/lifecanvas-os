"""API tests: authentication, CSRF, per-user authorisation, streaming, approvals, cancellation and restart recovery."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import HEADERS, INJECTION, signup, wait_run

PROTECTED = ["/api/bootstrap", "/api/runs", "/api/memory", "/api/actions", "/api/plans", "/api/providers", "/api/dev/graph", "/api/dev/telemetry", "/api/security", "/api/community/profile", "/api/threads", "/api/today"]


@pytest.mark.parametrize("path", PROTECTED)
def test_every_data_endpoint_requires_a_session(client, path):
    r = client.get(path)
    assert r.status_code == 401 and r.json()["error"] == "unauthenticated"


def test_health_and_static_client_are_public(client):
    assert client.get("/api/health").json()["status"] == "ok"
    r = client.get("/")
    assert r.status_code == 200 and "LifeCanvasOS" in r.text and "SUNSHINE EDITION" in r.text
    assert client.get("/static/app.js").status_code == 200 and client.get("/static/styles.css").status_code == 200


def test_security_headers_and_csp(client):
    h = client.get("/").headers
    assert "script-src 'self'" in h["content-security-policy"] and "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert client.get("/api/health").headers["cache-control"] == "no-store"


def test_the_web_client_has_no_inline_scripts_or_handlers():
    import pathlib
    import re
    web = pathlib.Path(__file__).resolve().parent.parent / "web"
    html = (web / "index.html").read_text()
    assert not re.search(r"<script(?![^>]*\bsrc=)", html) and not re.search(r"\son\w+=", html)
    for js in [web / "app.js", *sorted((web / "js").glob("*.js"))]:
        code = js.read_text()
        assert "innerHTML" not in code or "esc(" in code
        assert "eval(" not in code and "localStorage.setItem('lc-session'" not in code


def test_writes_require_the_csrf_header_and_same_origin(app):
    with TestClient(app) as raw:
        r = raw.post("/api/auth/register", json={"email": "a@b.co", "password": "sunshine-123"})
        assert r.status_code == 403
        r = raw.post("/api/auth/register", json={"email": "a@b.co", "password": "sunshine-123"}, headers={**HEADERS, "Origin": "https://evil.example"})
        assert r.status_code == 403


def test_untrusted_hosts_are_rejected(app):
    with TestClient(app, base_url="http://evil.example") as raw:
        assert raw.get("/api/health").status_code == 400


def test_register_login_logout_cycle(client):
    assert client.post("/api/auth/register", json={"email": "bad", "password": "sunshine-123"}).status_code == 400
    assert client.post("/api/auth/register", json={"email": "a@b.co", "password": "short"}).status_code == 400
    user = signup(client)
    cookie = client.cookies.get("lifecanvas_session")
    assert cookie and client.get("/api/me").json()["user"]["id"] == user["id"]
    assert client.post("/api/auth/register", json={"email": "asha@example.com", "password": "sunshine-123"}).status_code == 400
    client.post("/api/auth/logout")
    assert client.get("/api/me").status_code == 401
    client.cookies.set("lifecanvas_session", cookie)
    assert client.get("/api/me").status_code == 401  # the server-side session was revoked
    assert client.post("/api/auth/login", json={"email": "asha@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "asha@example.com", "password": "sunshine-123"}).status_code == 200


def test_session_cookie_is_httponly_and_strict(client):
    r = client.post("/api/auth/register", json={"email": "c@d.co", "password": "sunshine-123"})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert "pw_hash" not in r.text and "sunshine-123" not in r.text


def test_run_lifecycle_streams_events_and_returns_grounded_sections(client, user):
    started = client.post("/api/runs", json={"goal": "Find jazz and a vegetarian dinner this weekend", "city": "Delhi", "country": "IN"}).json()
    run = wait_run(client, started["run_id"])
    assert run["status"] == "completed" and run["result"]["total_cards"] > 0 and run["result"]["planner_mode"] == "rules"
    with client.stream("GET", f"/api/runs/{run['id']}/stream") as s:
        body = "".join(s.iter_text())
    kinds = [line.split(": ", 1)[1] for line in body.splitlines() if line.startswith("event: ")]
    assert kinds.count("step") >= 10 and kinds[-1] == "end" and "final" in kinds
    steps = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ") and '"kind": "step"' in line]
    assert [s["node"] for s in steps[:3]] == ["recall", "sentinel", "planner"]
    replay = client.get(f"/api/runs/{run['id']}/events?after={steps[4]['seq']}").json()["events"]
    assert replay and replay[0]["seq"] > steps[4]["seq"]  # resumable stream cursor
    assert len(client.get(f"/api/runs/{run['id']}/checkpoints").json()["checkpoints"]) >= 5
    assert client.get("/api/threads").json()["threads"][0]["id"] == started["thread_id"]


def test_blocked_requests_are_reported_and_logged(client, user):
    run = wait_run(client, client.post("/api/runs", json={"goal": INJECTION}).json()["run_id"])
    assert run["status"] == "blocked" and run["result"]["blocked"]
    sec = client.get("/api/security").json()
    assert sec["events"][0]["kind"] == "prompt_injection_blocked" and sec["chain"]["verified"]
    assert client.post("/api/discover", json={"domain": "dining", "query": INJECTION, "city": "Delhi"}).status_code == 400


def test_users_cannot_read_each_others_runs_memory_actions_or_plans(app, client, user):
    run = wait_run(client, client.post("/api/runs", json={"goal": "I love Thai food. Find dinner", "city": "Delhi", "workflow": "date_night"}).json()["run_id"])
    plan = client.post("/api/plans", json={"title": "Secret anniversary dinner"}).json()["id"]
    batch = client.post("/api/actions/propose", json={"items": [{"kind": "x", "payload": {"text": "private draft"}}]}).json()
    mem_id = client.get("/api/memory").json()["layers"]["preferences"][0]["id"]
    with TestClient(app, headers=HEADERS) as other:
        signup(other, "mallory@example.com", "Mallory")
        for path in (f"/api/runs/{run['id']}", f"/api/runs/{run['id']}/events", f"/api/runs/{run['id']}/stream", f"/api/runs/{run['id']}/checkpoints", f"/api/actions/{batch['actions'][0]['id']}/ledger"):
            assert other.get(path).status_code == 400, path
        assert other.post(f"/api/runs/{run['id']}/cancel").status_code == 400 and other.post(f"/api/runs/{run['id']}/resume").status_code == 400
        assert other.get("/api/runs").json()["runs"] == [] and other.get("/api/plans").json()["plans"] == [] and other.get("/api/actions").json()["actions"] == []
        assert all(v == [] for v in other.get("/api/memory").json()["layers"].values())
        assert other.get(f"/api/threads/{run['thread_id']}").json()["messages"] == []
        assert other.delete(f"/api/plans/{plan}").json()["deleted"] == 0 and other.delete(f"/api/memory/{mem_id}").json()["deleted"] == 0
        a = batch["actions"][0]
        assert other.post("/api/actions/decide", json={"batch_id": batch["batch_id"], "approve": [{"id": a["id"], "digest": a["digest"]}]}).status_code == 400
        assert other.post(f"/api/actions/{a['id']}/execute").status_code == 400
        hijack = other.post("/api/runs", json={"goal": "Find dinner", "city": "Delhi", "thread_id": run["thread_id"], "workflow": "date_night"}).json()
        assert hijack["thread_id"] != run["thread_id"]
    assert len(client.get("/api/plans").json()["plans"]) == 1 and client.get("/api/actions").json()["actions"][0]["status"] == "pending"


def test_approval_flow_over_http(client, user, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "token")
    run = wait_run(client, client.post("/api/runs", json={"goal": "Write a tweet about jazz and publish it"}).json()["run_id"])
    assert run["status"] == "awaiting_approval" and world.hits("api.x.com") == 0
    assert client.get("/api/bootstrap").json()["pending_approvals"] == 1
    a = next(x for x in client.get("/api/actions").json()["actions"] if x["batch_id"] == run["result"]["batch_id"])
    assert a["status"] == "pending" and a["platform"] == "X" and a["visibility"] == "Public" and a["connected"]
    bad = client.post("/api/actions/decide", json={"batch_id": a["batch_id"], "approve": [{"id": a["id"], "digest": "f" * 64}]}).json()
    assert bad["actions"][0]["status"] == "pending" and world.hits("api.x.com") == 0
    wait_run(client, run["id"], until=("awaiting_approval",))
    out = client.post("/api/actions/decide", json={"batch_id": a["batch_id"], "approve": [{"id": a["id"], "digest": a["digest"]}]}).json()
    assert out["actions"][0]["status"] == "executed" and world.hits("api.x.com", "POST") == 1
    done = wait_run(client, run["id"])
    assert done["status"] == "completed" and done["result"]["receipts"][0]["receipt"]
    assert client.post("/api/actions/decide", json={"batch_id": a["batch_id"], "approve": [{"id": a["id"], "digest": a["digest"]}]}).status_code == 400
    assert [x["state"] for x in client.get(f"/api/actions/{a['id']}/ledger").json()["ledger"]] == ["proposed", "digest_mismatch", "approved", "executing", "executed"]


def test_direct_batches_support_selective_approval(client, user, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TODOIST_API_TOKEN", "token")
    out = client.post("/api/actions/propose", json={"items": [{"kind": "x", "payload": {"text": "One"}}, {"kind": "todoist", "payload": {"title": "Two"}}, {"kind": "gmail", "payload": {"to": "nope", "subject": "s", "text": "t"}}]}).json()
    assert out["awaiting_approval"] and len(out["actions"]) == 2 and out["rejected"][0]["kind"] == "gmail"
    x, todo = out["actions"]
    res = client.post("/api/actions/decide", json={"batch_id": out["batch_id"], "approve": [{"id": todo["id"], "digest": todo["digest"]}], "reject": []}).json()
    assert {a["kind"]: a["status"] for a in res["actions"]} == {"x": "pending", "todoist": "executed"} and world.hits("api.x.com") == 0
    res = client.post("/api/actions/decide", json={"batch_id": out["batch_id"], "approve": [], "reject": [x["id"]]}).json()
    assert {a["kind"]: a["status"] for a in res["actions"]} == {"x": "rejected", "todoist": "executed"}


def test_discover_create_today_and_providers(client, user):
    d = client.post("/api/discover", json={"domain": "dining", "query": "", "city": "Delhi", "filters": {"amenity": "restaurant", "diets": ["vegetarian"]}}).json()
    assert d["status"] == "ok" and d["cards"][0]["title"] == "Trattoria Verde" and d["handoffs"] and d["trace"]
    assert all(h["kind"] == "handoff" and h["availability"] == "External app" for h in d["handoffs"])
    c = client.post("/api/create", json={"topic": "jazz", "platforms": ["x", "linkedin", "gmail"], "tone": "warm"}).json()
    variants = {v["platform"]: v for v in c["creative"]["variants"]}
    assert c["creative"]["mode"] == "assembled" and variants["x"]["chars"] <= 280 and variants["gmail"]["needs"] == "recipient email"
    assert {p["kind"] for p in c["proposals"]} == {"x", "linkedin"} and client.get("/api/actions").json()["actions"] == []  # drafting proposes nothing by itself
    t = client.get("/api/today?city=Delhi").json()
    assert t["weather"]["ok"] and t["movies"]["cards"] and t["fixtures"]["cards"]
    providers = {p["id"]: p for p in client.get("/api/providers").json()["providers"]}
    assert providers["ticketmaster"]["status"] == "configuration_required" and providers["zomato"]["status"] == "external_handoff"
    assert client.post("/api/providers/tvmaze/verify").json()["status"] == "connected_verified"
    assert client.post("/api/providers/nope/verify").status_code == 404
    tel = client.get("/api/dev/telemetry").json()
    assert tel["tools"] and tel["providers"] and tel["llm"] == []  # no model configured, so no token rows are invented
    g = client.get("/api/dev/graph").json()
    assert "action" in g["subgraphs"] and "graph TD" in g["mermaid"] and len(g["specialist_nodes"]) == 8


def test_memory_endpoints(client, user):
    wait_run(client, client.post("/api/runs", json={"goal": "I love Thai food and I support Arsenal. Explain the history of jazz", "workflow": "research"}).json()["run_id"])
    m = client.get("/api/memory").json()
    assert m["preferences"] == {"cuisine": ["Thai"], "team": ["Arsenal"]} and all(m["layers"][k] for k in m["layers"])
    assert client.get("/api/memory/recall?q=history of jazz music").json()["matches"]
    assert client.post("/api/memory/preferences", json={"kind": "diet", "value": "vegan"}).status_code == 200
    assert client.post("/api/memory/preferences", json={"kind": "diet", "value": INJECTION[:80]}).status_code == 400
    assert client.delete("/api/memory?layer=preferences").json()["deleted"] == 3 and client.get("/api/memory").json()["preferences"] == {}
    assert client.delete("/api/memory?layer=nope").status_code == 400


def test_community_is_opt_in_with_block_and_report(app, client, user):
    assert client.put("/api/community/profile", json={"display_name": "Asha", "city": "Delhi", "interests": ["jazz"], "discoverable": True, "adult_confirmed": False}).status_code == 400
    client.put("/api/community/profile", json={"display_name": "Asha", "city": "Delhi", "interests": ["jazz", "running"], "bio": "Mail me a@b.co", "discoverable": True, "adult_confirmed": True})
    with TestClient(app, headers=HEADERS) as bob, TestClient(app, headers=HEADERS) as cara:
        signup(bob, "bob@example.com", "Bob")
        signup(cara, "cara@example.com", "Cara")
        cara.put("/api/community/profile", json={"display_name": "Cara", "city": "Delhi", "interests": ["jazz"], "discoverable": False, "adult_confirmed": True})
        bob.put("/api/community/profile", json={"display_name": "Bob", "city": "Delhi", "interests": ["jazz", "coffee"], "discoverable": True, "adult_confirmed": True})
        found = bob.get("/api/community/matches").json()["matches"]
        assert [m["display_name"] for m in found] == ["Asha"] and found[0]["shared"] == ["jazz"] and found[0]["same_city"]
        assert "a@b.co" not in str(found) and "email" not in found[0] and "example.com" not in str(found)  # no contact details leak
        asha_id = found[0]["user_id"]
        assert cara.post("/api/community/requests", json={"user_id": asha_id}).status_code == 400  # must opt in first
        req = bob.post("/api/community/requests", json={"user_id": asha_id, "message": "Gig on Friday?"}).json()
        assert bob.post("/api/community/requests", json={"user_id": asha_id}).status_code == 400
        assert bob.post(f"/api/community/requests/{req['id']}", json={"accept": True}).status_code == 400  # only the recipient may accept
        assert client.get("/api/community/connections").json()["incoming"][0]["display_name"] == "Bob"
        assert client.post(f"/api/community/requests/{req['id']}", json={"accept": True}).json()["status"] == "accepted"
        bob_id = client.get("/api/community/connections").json()["connected"][0]["user_id"]
        assert client.post("/api/community/report", json={"user_id": bob_id, "reason": "spam"}).json()["blocked"]
        assert bob.get("/api/community/matches").json()["matches"] == [] and client.get("/api/community/connections").json()["connected"] == []
        d = client.post("/api/discover", json={"domain": "community", "query": "people who like jazz", "city": "Delhi"}).json()
        assert d["cards"] == []


def test_plans_crud(client, user):
    pid = client.post("/api/plans", json={"title": "Jazz night", "starts": "2026-12-05", "data": {"provider": "MusicBrainz", "url": "https://musicbrainz.org/event/e1"}}).json()["id"]
    assert client.get("/api/plans").json()["plans"][0]["data"]["provider"] == "MusicBrainz"
    assert client.delete(f"/api/plans/{pid}").json()["deleted"] == 1 and client.post("/api/plans", json={"title": ""}).status_code == 422


def test_account_deletion_erases_user_data(client, user):
    wait_run(client, client.post("/api/runs", json={"goal": "I love Thai food. Find dinner", "city": "Delhi", "workflow": "date_night"}).json()["run_id"])
    client.post("/api/plans", json={"title": "x"})
    db = client.app.state.svc.db
    assert client.delete("/api/me").json()["deleted"] and client.get("/api/me").status_code == 401
    for table in ("users", "sessions", "runs", "run_events", "memories", "messages", "threads", "plans", "tool_calls"):
        assert db.one(f"SELECT COUNT(*) n FROM {table}")["n"] == 0, table


def test_validation_and_limits(client, user):
    assert client.post("/api/runs", json={"goal": ""}).status_code == 422
    assert client.post("/api/runs", json={"goal": "x", "workflow": "nope"}).status_code == 400
    assert client.post("/api/discover", json={"domain": "action", "query": "x"}).status_code == 422
    assert client.post("/api/actions/propose", json={"items": []}).status_code == 422
    assert client.post("/api/runs", json={"goal": "x" * 1300}).status_code == 422
    assert client.post("/api/plans", content=b"x" * 250_000, headers={"Content-Type": "application/json"}).status_code == 413


def test_api_rate_limit(settings, world):
    from dataclasses import replace
    app = create_app(replace(settings, rate_limit_per_min=5), transport=httpx.MockTransport(world.handler))
    with TestClient(app, headers=HEADERS) as c:
        codes = [c.get("/api/health").status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[-1] == 429


def test_cancellation_stops_a_run(client, user, world):
    import time
    real = world.handler

    def slow(request):
        if request.url.host.startswith("overpass"):
            time.sleep(1.5)
        return real(request)

    client.app.state.svc.gateway._transport = httpx.MockTransport(slow)
    rid = client.post("/api/runs", json={"goal": "Find dinner", "city": "Delhi", "workflow": "date_night"}).json()["run_id"]
    assert client.post(f"/api/runs/{rid}/cancel").json()["status"] in ("cancelling", "cancelled")
    run = wait_run(client, rid, until=("cancelled", "completed"))
    assert run["status"] == "cancelled"
    assert client.post(f"/api/runs/{rid}/cancel").json()["status"] == "cancelled"  # idempotent


def test_restart_recovery_resumes_pending_approval_from_the_checkpoint(settings, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "token")
    make = lambda: create_app(settings, transport=httpx.MockTransport(world.handler))
    with TestClient(make(), headers=HEADERS) as first:
        signup(first)
        run = wait_run(first, first.post("/api/runs", json={"goal": "Write a tweet about jazz and publish it"}).json()["run_id"])
        assert run["status"] == "awaiting_approval"
    assert world.hits("api.x.com") == 0
    with TestClient(make(), headers=HEADERS) as second:  # a brand-new process on the same SQLite files
        assert second.post("/api/auth/login", json={"email": "asha@example.com", "password": "sunshine-123"}).status_code == 200
        again = second.get(f"/api/runs/{run['id']}").json()
        assert again["status"] == "awaiting_approval"
        a = next(x for x in second.get("/api/actions").json()["actions"] if x["status"] == "pending")
        second.post("/api/actions/decide", json={"batch_id": a["batch_id"], "approve": [{"id": a["id"], "digest": a["digest"]}]})
        done = wait_run(second, run["id"])
        assert done["status"] == "completed" and done["result"]["receipts"][0]["status"] == "executed" and world.hits("api.x.com", "POST") == 1


def test_restart_recovery_marks_and_resumes_interrupted_runs(settings, world):
    make = lambda: create_app(settings, transport=httpx.MockTransport(world.handler))
    with TestClient(make(), headers=HEADERS) as first:
        signup(first)
        run = wait_run(first, first.post("/api/runs", json={"goal": "Find dinner", "city": "Delhi", "workflow": "date_night"}).json()["run_id"])
        db = first.app.state.svc.db
        db.run("UPDATE runs SET status='running' WHERE id=?", (run["id"],))  # simulate a crash mid-run
        db.run("UPDATE actions SET status='executing' WHERE 0")
    with TestClient(make(), headers=HEADERS) as second:
        assert second.get("/api/health").json()["recovered"]["interrupted_runs"] == 1
        second.post("/api/auth/login", json={"email": "asha@example.com", "password": "sunshine-123"})
        assert second.get(f"/api/runs/{run['id']}").json()["status"] == "interrupted"
        assert second.post(f"/api/runs/{run['id']}/resume").json()["status"] == "running"
        assert wait_run(second, run["id"])["status"] == "completed"

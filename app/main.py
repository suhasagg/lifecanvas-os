"""FastAPI application: authenticated, user-scoped API over the LangGraph runtime, plus the Sunshine web client."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__, supervisor
from app.agents.nlu import understand
from app.config import Settings
from app.integrations.publish import EXTERNAL, LIMITS
from app.memory import LAYERS, Memory
from app.providers.base import Gateway
from app.providers.catalog import ALL
from app.providers.llm import ModelRouter
from app.providers.registry import Registry
from app.repositories.db import Database, dumps, loads, now
from app.runtime import RunError, Runtime
from app.security import Audit, Auth, RateLimiter, clean_text, redact, screen, security_event
from app.services import budget as budget_service
from app.services.actions import ActionError, Actions
from app.services.community import Community, CommunityError
from app.services.container import Services
from app.services.social import Social, SocialError
from app.subgraphs import creative, discovery, research
from app.tools import registry as tools

WEB = Path(__file__).resolve().parent.parent / "web"
COOKIE = "lifecanvas_session"
CSP = ("default-src 'self'; img-src 'self' https: data:; media-src https:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=60)


class RunIn(BaseModel):
    goal: str = Field(min_length=1, max_length=1200)
    city: str = Field(default="", max_length=60)
    country: str = Field(default="", max_length=2)
    workflow: str = Field(default="auto", max_length=20)
    strategy: str = Field(default="", max_length=12)
    thread_id: str = Field(default="", max_length=40)


class DiscoverIn(BaseModel):
    domain: Literal["entertainment", "dining", "travel", "culture", "community", "research"]
    query: str = Field(default="", max_length=300)
    city: str = Field(default="", max_length=60)
    country: str = Field(default="", max_length=2)
    filters: dict = Field(default_factory=dict)


class CreateIn(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    notes: str = Field(default="", max_length=2000)
    tone: Literal["warm", "professional", "playful", "bold"] = "warm"
    platforms: list[str] = Field(default_factory=lambda: ["linkedin"], max_length=6)
    to: str = Field(default="", max_length=254)
    channel: str = Field(default="", max_length=40)
    image_url: str = Field(default="", max_length=800)
    skip_research: bool = False


class ProposeIn(BaseModel):
    items: list[dict] = Field(min_length=1, max_length=12)


class DecideIn(BaseModel):
    batch_id: str = Field(max_length=40)
    approve: list[dict] = Field(default_factory=list, max_length=12)
    reject: list[str] = Field(default_factory=list, max_length=12)


class ProfileIn(BaseModel):
    display_name: str = Field(default="", max_length=40)
    city: str = Field(default="", max_length=60)
    interests: list[str] = Field(default_factory=list, max_length=20)
    bio: str = Field(default="", max_length=280)
    discoverable: bool = False
    adult_confirmed: bool = False


class PlanIn(BaseModel):
    kind: str = Field(default="saved", max_length=30)
    title: str = Field(min_length=1, max_length=160)
    starts: str = Field(default="", max_length=40)
    data: dict = Field(default_factory=dict)


class PreferenceIn(BaseModel):
    kind: Literal["cuisine", "artist", "team", "diet", "budget", "travel_style", "home_city", "interest"]
    value: str = Field(min_length=1, max_length=80)


def create_app(settings: Settings | None = None, transport=None) -> FastAPI:
    settings = settings or Settings.from_env()
    db = Database(settings.db_path)
    gateway = Gateway(settings, db, ALL, transport=transport)
    audit = Audit(db)
    svc = Services(settings, db, gateway, Registry(gateway, db), ModelRouter(gateway, db), Memory(db), audit, Community(db))
    svc.actions = Actions(db, gateway, audit, settings.approval_ttl_s)
    runtime, auth, limiter, login_limiter = Runtime(svc), Auth(db, settings.session_ttl_s), RateLimiter(settings.rate_limit_per_min), RateLimiter(10)
    specialists = {name: discovery.build(name, svc) for name in discovery.POLICIES} | {"research": research.build(svc)}
    creative_graph = creative.build(svc)
    social = Social(db, svc.community)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.recovered = await runtime.start()
        if os.getenv("LIFECANVAS_VERIFY_ON_START", "1") == "1":
            app.state.verify_task = asyncio.create_task(svc.registry.verify_all(only_configured=True))
        yield
        await runtime.stop()
        await gateway.close()

    app = FastAPI(title="LifeCanvasOS", version=__version__, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.svc, app.state.runtime, app.state.auth = svc, runtime, auth
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path, method = request.url.path, request.method
        client = request.client.host if request.client else "unknown"
        if path.startswith("/api/"):
            if not limiter.allow(client):
                return JSONResponse({"error": "rate_limited", "message": "Too many requests. Wait a minute and try again."}, 429, headers={"Retry-After": "60"})
            if method in ("POST", "PUT", "PATCH", "DELETE"):
                origin = request.headers.get("origin")
                same = origin is None or origin.split("://", 1)[-1] == request.headers.get("host") or origin in settings.allowed_origins
                if not same or request.headers.get("x-requested-with") != "lifecanvas":
                    security_event(db, None, "csrf_rejected", {"path": path, "origin": origin or ""})
                    return JSONResponse({"error": "forbidden", "message": "Cross-site request rejected"}, 403)
                if int(request.headers.get("content-length") or 0) > 200_000:
                    return JSONResponse({"error": "too_large", "message": "Request body is too large"}, 413)
        response = await call_next(request)
        response.headers.update({"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin-when-cross-origin",
                                 "Permissions-Policy": "geolocation=(), camera=(), microphone=()", "Cross-Origin-Opener-Policy": "same-origin"})
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RunError)
    @app.exception_handler(ActionError)
    @app.exception_handler(CommunityError)
    @app.exception_handler(SocialError)
    async def domain_error(_request: Request, exc: Exception):
        return JSONResponse({"error": "invalid_request", "message": str(exc)}, 400)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        return JSONResponse({"error": {401: "unauthenticated", 403: "forbidden", 404: "not_found"}.get(exc.status_code, "error"), "message": str(exc.detail)}, exc.status_code)

    def user(request: Request) -> dict:
        u = auth.resolve(request.cookies.get(COOKIE))
        if not u:
            raise HTTPException(401, "Sign in to continue")
        return u

    def set_session(response: Response, user_id: str) -> None:
        response.set_cookie(COOKIE, auth.issue(user_id), max_age=settings.session_ttl_s, httponly=True, samesite="strict", secure=settings.secure_cookies, path="/")

    # ------------------------------------------------------------------ auth
    @app.post("/api/auth/register")
    def register(body: Credentials, request: Request, response: Response):
        if not login_limiter.allow("reg:" + (request.client.host if request.client else "")):
            raise HTTPException(429, "Too many attempts")
        try:
            u = auth.register(body.email, body.name or body.email.split("@")[0], body.password)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        set_session(response, u["id"])
        audit.record(u["id"], "auth.registered", {})
        return {"user": u}

    @app.post("/api/auth/login")
    def login(body: Credentials, request: Request, response: Response):
        if not login_limiter.allow("login:" + body.email.lower()):
            raise HTTPException(429, "Too many attempts. Wait a minute.")
        try:
            u = auth.login(body.email, body.password)
        except PermissionError as exc:
            security_event(db, None, "login_failed", {"client": request.client.host if request.client else ""})
            raise HTTPException(401, str(exc)) from None
        set_session(response, u["id"])
        audit.record(u["id"], "auth.login", {})
        return {"user": u}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response):
        auth.revoke(request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    @app.get("/api/me")
    def me(u: dict = Depends(user)):
        return {"user": u}

    @app.delete("/api/me")
    async def delete_me(request: Request, response: Response, u: dict = Depends(user)):
        """Erase the account and every user-scoped record, including saved graph checkpoints."""
        uid = u["id"]
        await runtime.forget([r["id"] for r in db.all("SELECT id FROM runs WHERE user_id=?", (uid,))] + [r["run_id"] for r in db.all("SELECT DISTINCT run_id FROM actions WHERE user_id=?", (uid,))])
        with db.tx(immediate=True) as c:
            for table, col in (("messages", "user_id"), ("threads", "user_id"), ("memories", "user_id"), ("run_events", "user_id"), ("runs", "user_id"), ("ledger", "user_id"), ("actions", "user_id"), ("profiles", "user_id"),
                               ("plans", "user_id"), ("llm_calls", "user_id"), ("tool_calls", "user_id"), ("security_events", "user_id"), ("sessions", "user_id"), ("connections", "sender"), ("connections", "recipient"),
                               ("blocks", "blocker"), ("blocks", "blocked"), ("reports", "reporter"), ("meetup_members", "user_id"), ("meetups", "organiser"), ("users", "id")):
                c.execute(f"DELETE FROM {table} WHERE {col}=?", (uid,))
        audit.record(None, "account.deleted", {})
        response.delete_cookie(COOKIE, path="/")
        return {"deleted": True}

    # ------------------------------------------------------------------ bootstrap
    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "recovered": getattr(app.state, "recovered", {})}

    @app.get("/api/bootstrap")
    def bootstrap(u: dict = Depends(user)):
        providers = svc.registry.list()
        counts: dict[str, int] = {}
        for p in providers:
            counts[p["status"]] = counts.get(p["status"], 0) + 1
        return {"user": u, "version": __version__, "workflows": [{"id": k, **{x: v[x] for x in ("label", "about")}, "specialists": list(v["specialists"])} for k, v in supervisor.WORKFLOWS.items()],
                "provider_counts": counts, "models": svc.router.describe(settings.routing_strategy), "preferences": svc.memory.preferences(u["id"]), "profile": svc.community.profile(u["id"]),
                "pending_approvals": sum(1 for a in svc.actions.list(u["id"]) if a["status"] == "pending"), "layers": list(LAYERS), "platforms": dict(LIMITS), "action_kinds": list(EXTERNAL)}

    # ------------------------------------------------------------------ runs
    @app.post("/api/runs")
    async def start_run(body: RunIn, u: dict = Depends(user)):
        return runtime.submit(u["id"], body.goal, body.city, body.country, body.workflow, body.strategy, body.thread_id)

    @app.get("/api/runs")
    def list_runs(u: dict = Depends(user)):
        return {"runs": runtime.list(u["id"])}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, u: dict = Depends(user)):
        return runtime.get(u["id"], run_id)

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str, after: int = 0, u: dict = Depends(user)):
        run = runtime.get(u["id"], run_id)
        return {"status": run["status"], "events": runtime.events(u["id"], run_id, after)}

    @app.get("/api/runs/{run_id}/stream")
    async def stream(run_id: str, request: Request, after: int = 0, u: dict = Depends(user)):
        runtime.get(u["id"], run_id)

        async def gen():
            cursor, idle = after, 0
            while not await request.is_disconnected():
                rows = runtime.events(u["id"], run_id, cursor)
                for r in rows:
                    cursor = r["seq"]
                    yield f"id: {r['seq']}\nevent: {r['kind']}\ndata: {json.dumps(r)}\n\n"
                status = runtime.get(u["id"], run_id)["status"]
                if not rows and status != "running":
                    yield f"event: end\ndata: {json.dumps({'status': status})}\n\n"
                    return
                idle = 0 if rows else idle + 1
                if idle and idle % 40 == 0:
                    yield ": keep-alive\n\n"
                await asyncio.sleep(0.25)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.post("/api/runs/{run_id}/cancel")
    async def cancel_run(run_id: str, u: dict = Depends(user)):
        return runtime.cancel(u["id"], run_id)

    @app.post("/api/runs/{run_id}/resume")
    async def resume_run(run_id: str, u: dict = Depends(user)):
        return runtime.resume(u["id"], run_id)

    @app.get("/api/runs/{run_id}/checkpoints")
    async def run_checkpoints(run_id: str, u: dict = Depends(user)):
        return {"checkpoints": await runtime.checkpoints(u["id"], run_id)}

    # ------------------------------------------------------------------ workspace discovery (direct specialist subgraph invocation)
    async def run_specialist(u: dict, domain: str, query: str, city: str, country: str, filters: dict) -> dict:
        if screen(query)["blocked"]:
            security_event(db, u["id"], "prompt_injection_blocked", {"where": "discover"})
            raise HTTPException(400, "This search matched safety rules and was not run")
        prefs = svc.memory.preferences(u["id"])
        params = {k: v for k, v in understand(query, city or prefs.get("home_city", [""])[-1], country).items() if k != "scores"}
        allowed = {"cuisines", "diets", "genres", "sport", "team", "amenity", "topic", "origin", "destination", "interests", "wants_movies", "wants_shows", "wants_music", "wants_events", "wants_flights", "wants_books",
                   "wants_art", "wants_fitness", "when", "budget"}
        params.update({k: v for k, v in filters.items() if k in allowed})
        if city:
            params["city"], params["country"] = clean_text(city, 60), country
        task = {"id": "d-" + uuid.uuid4().hex[:8], "specialist": domain, "objective": query or domain, "query": params.get("topic") or query, "params": params}
        out = await specialists[domain].ainvoke({"user_id": u["id"], "run_id": task["id"], "task": task, "preferences": prefs, "strategy": settings.routing_strategy})
        return out["results"][0] | {"trace": [{"node": t["node"], "summary": t["summary"]} for t in out["trace"]]}

    @app.post("/api/discover")
    async def discover(body: DiscoverIn, u: dict = Depends(user)):
        return await run_specialist(u, body.domain, clean_text(body.query, 300), body.city, body.country.upper(), body.filters)

    @app.get("/api/today")
    async def today(city: str = "", country: str = "", u: dict = Depends(user)):
        prefs = svc.memory.preferences(u["id"])
        city = clean_text(city, 60) or prefs.get("home_city", [""])[-1]
        ctx = svc.tool_ctx(u["id"], "today")
        team = (prefs.get("team") or [""])[-1]
        calls = [tools.call(ctx, "entertainment", "movies_charts", {"country": (country or "us").lower()}), tools.call(ctx, "entertainment", "sports_fixtures", {"sport": "football", "team": team})]
        if city:
            calls.append(tools.call(ctx, "travel", "weather", {"city": city, "country": country.upper()}))
        obs = await asyncio.gather(*calls)
        return {"city": city, "movies": obs[0], "fixtures": obs[1], "weather": obs[2] if city else None, "plans": plans(u)["plans"][:4],
                "pending_approvals": [a for a in svc.actions.list(u["id"]) if a["status"] == "pending"][:4], "recent_runs": runtime.list(u["id"], 4), "preferences": prefs}

    @app.post("/api/create")
    async def create(body: CreateIn, u: dict = Depends(user)):
        if screen(body.topic + " " + body.notes)["blocked"]:
            raise HTTPException(400, "This brief matched safety rules and was not processed")
        params = body.model_dump() | {"topic": clean_text(body.topic, 200), "notes": redact(clean_text(body.notes, 2000)), "propose_publish": True}
        task = {"id": "c-" + uuid.uuid4().hex[:8], "specialist": "creative", "objective": params["topic"], "query": params["topic"], "params": params}
        out = await creative_graph.ainvoke({"user_id": u["id"], "run_id": task["id"], "task": task, "strategy": settings.routing_strategy})
        return out["results"][0] | {"trace": [{"node": t["node"], "summary": t["summary"]} for t in out["trace"]]}

    # ------------------------------------------------------------------ providers
    @app.get("/api/providers")
    def providers(u: dict = Depends(user)):
        return {"providers": svc.registry.list(), "models": svc.router.describe(settings.routing_strategy)}

    @app.post("/api/providers/{provider_id}/verify")
    async def verify_provider(provider_id: str, u: dict = Depends(user)):
        if provider_id not in ALL:
            raise HTTPException(404, "Unknown provider")
        return await svc.registry.verify(provider_id)

    @app.post("/api/providers/verify-all")
    async def verify_all(u: dict = Depends(user)):
        return {"providers": await svc.registry.verify_all(only_configured=True)}

    # ------------------------------------------------------------------ memory
    @app.get("/api/memory")
    def memory(u: dict = Depends(user)):
        return {"layers": svc.memory.inspect(u["id"]), "preferences": svc.memory.preferences(u["id"])}

    @app.get("/api/memory/recall")
    def memory_recall(q: str, u: dict = Depends(user)):
        return {"query": q[:200], "matches": svc.memory.recall(u["id"], q[:200], touch=False)}

    @app.post("/api/memory/preferences")
    def add_preference(body: PreferenceIn, u: dict = Depends(user)):
        item = svc.memory.remember(u["id"], "preferences", f"{body.kind}:{body.value.lower()}", body.value, {"kind": body.kind, "source": "added by you"})
        if not item:
            raise HTTPException(400, "That value could not be stored")
        return item

    @app.delete("/api/memory/{memory_id}")
    def forget_one(memory_id: str, u: dict = Depends(user)):
        n = svc.memory.forget(u["id"], memory_id=memory_id)
        audit.record(u["id"], "memory.deleted", {"id": memory_id, "rows": n})
        return {"deleted": n}

    @app.delete("/api/memory")
    def forget_layer(layer: str, u: dict = Depends(user)):
        if layer not in LAYERS:
            raise HTTPException(400, "Unknown memory layer")
        n = svc.memory.forget(u["id"], layer=layer)
        audit.record(u["id"], "memory.layer_cleared", {"layer": layer, "rows": n})
        return {"deleted": n}

    @app.get("/api/threads")
    def threads(u: dict = Depends(user)):
        return {"threads": svc.memory.threads(u["id"])}

    @app.get("/api/threads/{thread_id}")
    def thread(thread_id: str, u: dict = Depends(user)):
        return {"messages": svc.memory.conversation(u["id"], thread_id, 60)}

    # ------------------------------------------------------------------ actions
    @app.get("/api/actions")
    def actions(u: dict = Depends(user)):
        return {"actions": svc.actions.list(u["id"])}

    @app.post("/api/actions/propose")
    async def propose(body: ProposeIn, u: dict = Depends(user)):
        return await runtime.propose(u["id"], body.items)

    @app.post("/api/actions/decide")
    async def decide(body: DecideIn, u: dict = Depends(user)):
        return await runtime.decide(u["id"], body.batch_id, body.approve, body.reject)

    @app.post("/api/actions/{action_id}/execute")
    async def execute(action_id: str, u: dict = Depends(user)):
        """Run an already-approved action that was held (for example because its provider was not yet connected)."""
        return await svc.actions.execute(u["id"], action_id)

    @app.get("/api/actions/{action_id}/ledger")
    def ledger(action_id: str, u: dict = Depends(user)):
        return {"action": svc.actions.get(u["id"], action_id), "ledger": svc.actions.ledger(u["id"], action_id)}

    # ------------------------------------------------------------------ community
    @app.get("/api/community/profile")
    def profile(u: dict = Depends(user)):
        return {"profile": svc.community.profile(u["id"])}

    @app.put("/api/community/profile")
    def save_profile(body: ProfileIn, u: dict = Depends(user)):
        audit.record(u["id"], "community.profile_saved", {"discoverable": body.discoverable})
        return {"profile": svc.community.save_profile(u["id"], **body.model_dump())}

    @app.get("/api/community/matches")
    def matches(interests: str = "", city: str = "", u: dict = Depends(user)):
        return {"matches": svc.community.matches(u["id"], [i.strip() for i in interests.split(",") if i.strip()] or None, city), "profile": svc.community.profile(u["id"])}

    @app.get("/api/community/connections")
    def connections(u: dict = Depends(user)):
        return svc.community.connections(u["id"]) | {"blocked": svc.community.blocked(u["id"])}

    @app.post("/api/community/requests")
    def connect(body: dict, u: dict = Depends(user)):
        return svc.community.request(u["id"], str(body.get("user_id", ""))[:40], str(body.get("message", "")))

    @app.post("/api/community/requests/{connection_id}")
    def respond(connection_id: str, body: dict, u: dict = Depends(user)):
        return svc.community.respond(u["id"], connection_id, bool(body.get("accept")))

    @app.post("/api/community/block")
    def block(body: dict, u: dict = Depends(user)):
        svc.community.block(u["id"], str(body.get("user_id", ""))[:40])
        audit.record(u["id"], "community.blocked", {})
        return {"blocked": True}

    @app.post("/api/community/unblock")
    def unblock(body: dict, u: dict = Depends(user)):
        svc.community.unblock(u["id"], str(body.get("user_id", ""))[:40])
        return {"blocked": False}

    @app.post("/api/community/report")
    def report(body: dict, u: dict = Depends(user)):
        audit.record(u["id"], "community.reported", {})
        return svc.community.report(u["id"], str(body.get("user_id", ""))[:40], str(body.get("reason", "")))

    # ------------------------------------------------------------------ budget, social agents, video calls
    @app.post("/api/budget/plan")
    def budget_plan(body: dict, u: dict = Depends(user)):
        cards = body.get("cards") if isinstance(body.get("cards"), list) else []
        try:
            return budget_service.plan([c for c in cards[:200] if isinstance(c, dict) and c.get("title")], float(body.get("budget") or 0), str(body.get("currency") or "")[:3], min(3, int(body.get("per_category") or 1)))
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, str(exc)) from None

    @app.get("/api/meetups")
    def meetups(u: dict = Depends(user)):
        return {"meetups": social.list(u["id"])}

    @app.post("/api/meetups")
    def create_meetup(body: dict, u: dict = Depends(user)):
        audit.record(u["id"], "meetup.created", {})
        return social.create(u["id"], str(body.get("title", "")), body.get("options") or [], [str(i)[:40] for i in body.get("invitees") or []], body.get("constraints") or {})

    @app.post("/api/meetups/{meetup_id}/constraints")
    def meetup_constraints(meetup_id: str, body: dict, u: dict = Depends(user)):
        return social.set_constraints(u["id"], meetup_id, body.get("constraints") or {})

    @app.post("/api/meetups/{meetup_id}/confirm")
    def meetup_confirm(meetup_id: str, u: dict = Depends(user)):
        return social.confirm(u["id"], meetup_id)

    @app.post("/api/community/call")
    def video_call(body: dict, u: dict = Depends(user)):
        audit.record(u["id"], "community.call_started", {})
        return social.call_with(u["id"], str(body.get("user_id", ""))[:40])

    # ------------------------------------------------------------------ plans
    @app.get("/api/plans")
    def plans(u: dict = Depends(user)):
        rows = db.all("SELECT id,kind,title,data,starts,created FROM plans WHERE user_id=? ORDER BY created DESC LIMIT 100", (u["id"],))
        for r in rows:
            r["data"] = loads(r["data"], {})
        return {"plans": rows}

    @app.post("/api/plans")
    def save_plan(body: PlanIn, u: dict = Depends(user)):
        if len(dumps(body.data)) > 60_000:
            raise HTTPException(413, "Plan is too large")
        pid = uuid.uuid4().hex
        db.run("INSERT INTO plans VALUES(?,?,?,?,?,?,?)", (pid, u["id"], clean_text(body.kind, 30), clean_text(body.title, 160), dumps(body.data), clean_text(body.starts, 40), now()))
        return {"id": pid}

    @app.delete("/api/plans/{plan_id}")
    def delete_plan(plan_id: str, u: dict = Depends(user)):
        return {"deleted": db.run("DELETE FROM plans WHERE id=? AND user_id=?", (plan_id, u["id"]))}

    # ------------------------------------------------------------------ developer and safety views
    @app.get("/api/dev/graph")
    def dev_graph(u: dict = Depends(user)):
        g = runtime.graph.get_graph(xray=1)
        return {"mermaid": g.draw_mermaid(), "nodes": sorted(g.nodes), "edges": len(g.edges), "subgraphs": sorted([*specialists, "creative", "action"]),
                "specialist_nodes": {n: sorted(x for x in sg.get_graph().nodes if not x.startswith("__")) for n, sg in (specialists | {"creative": creative_graph, "action": runtime.action_graph}).items()}}

    @app.get("/api/dev/tools")
    def dev_tools(u: dict = Depends(user)):
        return {"tools": tools.catalog(), "allowlists": {a: sorted(s) for a, s in tools.ALLOW.items()}, "write_tools": sorted(tools.WRITE_TOOLS)}

    @app.get("/api/dev/telemetry")
    def telemetry(u: dict = Depends(user)):
        uid = u["id"]
        return {
            "llm": db.all("SELECT provider,model,agent,COUNT(*) calls,SUM(ok) ok,SUM(prompt_tokens) prompt_tokens,SUM(completion_tokens) completion_tokens,ROUND(SUM(cost_usd),6) cost_usd,ROUND(AVG(latency_ms),1) avg_latency_ms "
                          "FROM llm_calls WHERE user_id=? GROUP BY provider,model,agent ORDER BY calls DESC", (uid,)),
            "tools": db.all("SELECT agent,tool,provider,COUNT(*) calls,SUM(ok) ok,SUM(items) items,ROUND(AVG(latency_ms),1) avg_latency_ms,MAX(latency_ms) max_latency_ms FROM tool_calls WHERE user_id=? GROUP BY agent,tool ORDER BY calls DESC", (uid,)),
            "providers": db.all("SELECT provider,COUNT(*) calls,SUM(ok) ok,SUM(cached) cached,SUM(retries) retries,ROUND(AVG(CASE WHEN cached=0 THEN latency_ms END),1) avg_latency_ms FROM provider_calls GROUP BY provider ORDER BY calls DESC"),
            "runs": db.all("SELECT status,COUNT(*) n,ROUND(AVG(updated-created),2) avg_seconds FROM runs WHERE user_id=? GROUP BY status", (uid,)),
            "note": "All figures are measured from this installation's own call logs. Token and cost rows appear only after a configured model provider has been called.",
        }

    @app.get("/api/security")
    def security(u: dict = Depends(user)):
        events = db.all("SELECT kind,detail,created FROM security_events WHERE user_id=? ORDER BY id DESC LIMIT 40", (u["id"],))
        for e in events:
            e["detail"] = loads(e["detail"], {})
        return {"events": events, "audit": audit.entries(u["id"], 40), "chain": audit.verify(),
                "controls": [{"name": n, "detail": d} for n, d in (
                    ("Sentinel screening", "Requests and retrieved text are screened for injection patterns. Pattern matching is a first line of defence, not a complete one."),
                    ("Least-privilege tools", f"{len(tools.TOOLS)} read tools across {len(tools.ALLOW)} agent allowlists; {len(tools.WRITE_TOOLS)} write tools reachable only from the action executor."),
                    ("Human approval", f"Every external write needs approval bound to a SHA-256 payload digest, valid for {settings.approval_ttl_s // 60} minutes, single use."),
                    ("Untrusted content", "Provider text is treated as data: instruction-like text is withheld from prompts and memory."),
                    ("Outbound requests", "HTTPS only, per-provider host allowlists, no redirects to private networks for user-supplied hosts."),
                    ("Sessions", "HttpOnly, SameSite=Strict cookies; PBKDF2 password hashes; CSRF header and Origin checks on writes."),
                    ("Audit", "Hash-chained audit log; verification status shown above."))]}

    @app.post("/api/security/screen")
    def screen_text(body: dict, u: dict = Depends(user)):
        text = str(body.get("text", ""))[:4000]
        return {"verdict": screen(text), "redacted": redact(text)}

    # ------------------------------------------------------------------ web client
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app() if os.getenv("LIFECANVAS_NO_AUTOAPP") != "1" else None

"""Architecture tests: native LangGraph structure, parallel fan-out, bounded loops, interrupts, checkpoints, isolation."""
import ast
import pathlib

import httpx
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app import supervisor
from app.config import Settings
from app.memory import Memory
from app.providers.base import Gateway
from app.providers.catalog import ALL
from app.providers.llm import ModelRouter
from app.providers.registry import Registry
from app.repositories.db import Database
from app.security import Audit
from app.services.actions import Actions
from app.services.community import Community
from app.services.container import Services
from app.subgraphs import action, creative, discovery, research
from app.tools import registry as tools
from tests.conftest import INJECTION

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def svc(tmp_path, world):
    db, st = Database(str(tmp_path / "g.db")), Settings(tool_deadline_s=5.0)
    gw = Gateway(st, db, ALL, transport=httpx.MockTransport(world.handler))

    async def no_sleep(_s):
        return None

    gw.sleep = no_sleep
    audit = Audit(db)
    s = Services(st, db, gw, Registry(gw, db), ModelRouter(gw, db), Memory(db), audit, Community(db))
    s.actions = Actions(db, gw, audit)
    return s


def inputs(goal, run="r1", user="u1", workflow="auto"):
    return {"user_id": user, "thread_id": "th-" + user, "run_id": run, "goal": goal, "city": "Delhi", "country": "IN", "workflow": workflow}


def cfg(run="r1"):
    return {"configurable": {"thread_id": run}}


def nodes(trace):
    return [t["node"] for t in trace]


# ------------------------------------------------------------------ structure
def test_supervisor_is_a_native_compiled_stategraph_with_subgraph_nodes(svc):
    g = supervisor.build(svc)
    assert isinstance(g, CompiledStateGraph)
    top = set(g.get_graph().nodes)
    assert {"recall", "sentinel", "refuse", "planner", "critic", "redispatch", "composer", "action", "consolidate"} <= top
    assert {"entertainment", "dining", "travel", "community", "culture", "research", "creative"} <= top
    expanded = set(g.get_graph(xray=1).nodes)
    for expected in ("dining:resolve", "dining:select", "dining:act", "dining:observe", "dining:rank", "research:plan_queries", "research:verify", "creative:critique", "action:gate", "action:execute"):
        assert expected in expanded, expected


def test_every_specialist_is_an_independently_compiled_graph_with_real_transitions(svc):
    graphs = {n: discovery.build(n, svc) for n in discovery.POLICIES} | {"research": research.build(svc), "creative": creative.build(svc), "action": action.build(svc)}
    assert len(graphs) == 8
    for name, g in graphs.items():
        assert isinstance(g, CompiledStateGraph), name
        drawn = g.get_graph()
        assert len([n for n in drawn.nodes if not n.startswith("__")]) >= 5, name
        assert any(e.conditional for e in drawn.edges), f"{name} has no conditional edge"


def test_graph_code_uses_langgraph_primitives_not_renamed_functions():
    src = {p.name: p.read_text() for p in [ROOT / "app/supervisor.py", *sorted((ROOT / "app/subgraphs").glob("*.py"))]}
    assert "Send(" in src["supervisor.py"] and "add_conditional_edges" in src["supervisor.py"] and "RetryPolicy" in src["supervisor.py"]
    assert "Send(" in src["research.py"] and "interrupt(" in src["action.py"]
    for name in ("discovery.py", "research.py", "creative.py", "action.py"):
        assert "StateGraph(" in src[name] and ".compile(" in src[name], name


def test_state_is_typed_with_reducers():
    from typing import get_type_hints

    from app.state import SpecialistState, SupervisorState
    hints = get_type_hints(SupervisorState, include_extras=True)
    assert hasattr(hints["results"], "__metadata__") and hasattr(hints["trace"], "__metadata__")
    assert hasattr(get_type_hints(SpecialistState, include_extras=True)["observations"], "__metadata__")


# ------------------------------------------------------------------ behaviour
async def test_parallel_specialists_run_and_results_are_grounded(svc, world):
    out = await supervisor.build(svc, MemorySaver()).ainvoke(inputs("Find jazz concerts and a vegetarian Italian dinner this weekend"), cfg())
    assert out["status"] == "completed"
    sections = {s["specialist"]: s for s in out["answer"]["sections"]}
    assert set(sections) == {"entertainment", "dining"} and out["plan"]["mode"] == "rules"
    order = nodes(out["trace"])
    assert order[:3] == ["recall", "sentinel", "planner"] and order[-3:] == ["critic", "composer", "consolidate"]
    assert order.index("dining.report") < order.index("critic") and order.index("entertainment.report") < order.index("critic")
    for s in sections.values():
        assert s["cards"]
        for c in s["cards"]:
            assert c["provider"] and c["url"].startswith("https://") and c["retrieved_at"]
    top = sections["dining"]["cards"][0]
    assert top["title"] == "Trattoria Verde" and "dietary option listed by the source" in top["why"]
    assert {n["provider_id"] for n in sections["dining"]["notices"]} == {"google_places", "foursquare"}  # honest configuration-required notices
    assert out["critique"]["approved"] and out["critique"]["score"] == 1.0


async def test_sentinel_blocks_before_any_tool_or_model_call(svc, world):
    out = await supervisor.build(svc, MemorySaver()).ainvoke(inputs(INJECTION), cfg())
    assert out["status"] == "blocked" and out["answer"]["blocked"] and world.calls == []
    assert nodes(out["trace"]) == ["recall", "sentinel", "refuse", "consolidate"]
    assert svc.db.one("SELECT COUNT(*) n FROM tool_calls")["n"] == 0 and svc.db.one("SELECT kind FROM security_events")["kind"] == "prompt_injection_blocked"
    assert svc.memory.inspect("u1")["episodic"] == [] and svc.memory.preferences("u1") == {}


async def test_critic_triggers_bounded_revision_on_transient_failure(svc, world):
    for host in ("overpass-api.de", "overpass.private.coffee", "nominatim.openstreetmap.org"):
        world.fail[host] = 503
    world.fail_times.update({"overpass-api.de": 1, "overpass.private.coffee": 1, "nominatim.openstreetmap.org": 2})
    out = await supervisor.build(svc, MemorySaver()).ainvoke(inputs("vegetarian dinner", workflow="date_night"), cfg())
    order = nodes(out["trace"])
    assert out["revision"] <= svc.settings.max_revisions and order.count("redispatch") <= svc.settings.max_revisions
    assert order.count("critic") <= svc.settings.max_revisions + 1 and out["status"] == "completed"


async def test_specialist_loops_are_bounded_when_providers_stay_down(svc, world):
    for host in ("overpass-api.de", "overpass.private.coffee", "nominatim.openstreetmap.org"):
        world.fail[host] = 503
    out = await supervisor.build(svc, MemorySaver()).ainvoke(inputs("dinner", workflow="date_night"), cfg())
    order = nodes(out["trace"])
    assert order.count("dining.select") <= 2 * (svc.settings.max_revisions + 1) and order.count("redispatch") == svc.settings.max_revisions
    dining = next(s for s in out["answer"]["sections"] if s["specialist"] == "dining")
    assert dining["status"] == "failed" and dining["cards"] == [] and dining["errors"]
    assert not out["critique"]["approved"]  # degraded, reported honestly, not replaced with sample data


async def test_external_actions_interrupt_and_resume_with_command(svc, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "token")
    g = supervisor.build(svc, MemorySaver())
    out = await g.ainvoke(inputs("Write a tweet about jazz and publish it"), cfg())
    request = out["__interrupt__"][0].value
    assert request["type"] == "approval_required" and [a["kind"] for a in request["actions"]] == ["x"]
    assert world.hits("api.x.com") == 0 and (await g.aget_state(cfg())).next == ("action",)
    a = request["actions"][0]
    out = await g.ainvoke(Command(resume={"approve": [{"id": a["id"], "digest": a["digest"]}], "reject": []}), cfg())
    assert out["status"] == "completed" and world.hits("api.x.com", "POST") == 1
    assert out["answer"]["receipts"][0]["status"] == "executed" and out["answer"]["receipts"][0]["receipt"]


async def test_rejection_sends_nothing(svc, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "token")
    g = supervisor.build(svc, MemorySaver())
    out = await g.ainvoke(inputs("Write a tweet about jazz and publish it"), cfg())
    a = out["__interrupt__"][0].value["actions"][0]
    out = await g.ainvoke(Command(resume={"approve": [], "reject": [a["id"]]}), cfg())
    assert out["answer"]["receipts"][0]["status"] == "rejected" and world.hits("api.x.com") == 0


async def test_wrong_digest_on_resume_executes_nothing(svc, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "token")
    g = action.build(svc, MemorySaver())
    out = await g.ainvoke({"user_id": "u1", "run_id": "act-1", "proposals": [{"kind": "x", "payload": {"text": "hello"}}]}, cfg("act-1"))
    a = out["__interrupt__"][0].value["actions"][0]
    out = await g.ainvoke(Command(resume={"approve": [{"id": a["id"], "digest": "0" * 64}], "reject": []}), cfg("act-1"))
    assert "__interrupt__" in out and world.hits("api.x.com") == 0  # still pending: the gate re-opens


async def test_threads_and_users_are_isolated(svc):
    g = supervisor.build(svc, MemorySaver())
    await g.ainvoke(inputs("I love Thai food. Find dinner", run="ra", user="alice", workflow="date_night"), cfg("ra"))
    out = await g.ainvoke(inputs("Find dinner", run="rb", user="bob", workflow="date_night"), cfg("rb"))
    assert out["preferences"] == {} and out["memories"] == [] and out["history"] == []
    assert (await g.aget_state(cfg("ra"))).values["user_id"] == "alice" and (await g.aget_state(cfg("rb"))).values["user_id"] == "bob"
    again = await g.ainvoke(inputs("Find dinner again", run="rc", user="alice", workflow="date_night"), cfg("rc"))
    assert again["preferences"]["cuisine"] == ["Thai"] and again["memories"] and len(again["history"]) == 2


async def test_memory_consolidation_writes_all_persistent_layers(svc):
    await supervisor.build(svc, MemorySaver()).ainvoke(inputs("I love Italian food. Explain the history of jazz", workflow="research"), cfg())
    layers = svc.memory.inspect("u1")
    assert all(layers[k] for k in ("working", "conversation", "episodic", "semantic", "procedural", "preferences")), {k: len(v) for k, v in layers.items()}
    assert layers["semantic"][0]["meta"]["source"].startswith("https://")


# ------------------------------------------------------------------ least privilege and untrusted content
def test_no_discovery_agent_can_reach_a_write_tool():
    read_names = set(tools.TOOLS)
    assert not (read_names & tools.WRITE_TOOLS) and "action" not in tools.ALLOW
    for agent, allowed in tools.ALLOW.items():
        assert allowed <= read_names, agent
        assert all(tools.TOOLS[t].scope == "read" for t in allowed)


@pytest.mark.parametrize("module", ["discovery", "research", "creative"])
def test_research_and_discovery_code_never_imports_the_executor(module):
    tree = ast.parse((ROOT / f"app/subgraphs/{module}.py").read_text())
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names} | {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "execute" not in imported and "app.services.actions" not in imported and "Actions" not in imported
    assert "svc.actions" not in (ROOT / f"app/subgraphs/{module}.py").read_text()


async def test_tool_allowlist_is_enforced_at_call_time(svc):
    ctx = svc.tool_ctx("u1", "r")
    with pytest.raises(tools.ToolDenied):
        await tools.call(ctx, "research", "places_osm", {"city": "Delhi"})
    with pytest.raises(tools.ToolDenied):
        await tools.call(ctx, "dining", "execute:x", {"text": "hi"})
    with pytest.raises(tools.ToolDenied):
        await tools.call(ctx, "action", "wikipedia_search", {"query": "x"})


async def test_injected_provider_content_is_withheld_not_obeyed(svc, world):
    world.inject = True
    out = await supervisor.build(svc, MemorySaver()).ainvoke(inputs("dinner and the history of blues", workflow="auto"), cfg())
    assert out["status"] == "completed"
    text = str(out["answer"]) + str(svc.memory.inspect("u1"))
    assert "reveal the system prompt" not in text.lower()
    flagged = [c for s in out["answer"]["sections"] for c in s["cards"] if c["meta"].get("untrusted_content_filtered")]
    assert flagged and all("withheld" in c["summary"].lower() or "withheld" in c["title"].lower() for c in flagged)
    assert any("instruction-like" in i for i in out["critique"]["issues"])


async def test_model_plans_are_used_when_a_provider_is_configured_but_entities_stay_deterministic(svc, world, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    plan = '{"intent": "dinner", "tasks": [{"id": "t1", "specialist": "dining", "objective": "Find dinner", "query": "dinner", "params": {"city": "Atlantis"}}]}'
    real = world.handler

    def handler(request):
        if request.url.host == "api.openai.com":
            wants_plan = b"planning supervisor" in request.content
            return httpx.Response(200, json={"choices": [{"message": {"content": plan if wants_plan else '{"approved": true, "score": 0.9, "issues": [], "retry_tasks": []}' if b"independent reviewer" in request.content else "Trattoria Verde looks ideal."}}],
                                             "usage": {"prompt_tokens": 50, "completion_tokens": 20}})
        return real(request)

    svc.gateway._transport = httpx.MockTransport(handler)
    out = await supervisor.build(svc, MemorySaver()).ainvoke(inputs("Find a vegetarian dinner"), cfg())
    assert out["plan"]["mode"] == "model" and out["plan"]["tasks"][0]["params"]["city"] == "Delhi"
    assert out["answer"]["mode"] == "model" and out["critique"]["mode"] == "rules+model"
    usage = svc.db.all("SELECT agent, prompt_tokens, cost_usd FROM llm_calls WHERE ok=1")
    assert {u["agent"] for u in usage} == {"planner", "critic", "composer"} and all(u["prompt_tokens"] == 50 and u["cost_usd"] > 0 for u in usage)


def test_production_code_contains_no_demo_data_paths():
    banned = ("demo", "mock", "fake", "sample data", "lorem", "placeholder result", "simulat")
    for path in (ROOT / "app").rglob("*.py"):
        code = "\n".join(line for line in path.read_text().lower().splitlines() if not line.strip().startswith(("#", '"""')) and "never" not in line and "no sample" not in line and "not sample" not in line)
        for word in banned:
            assert word not in code, f"{path.name} contains '{word}'"

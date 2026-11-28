import httpx
import pytest

from app.config import Settings
from app.providers.base import Gateway, ProviderError, Status
from app.providers.catalog import ALL, HANDOFFS, SPECS
from app.providers.llm import LLMUnavailable, ModelRouter
from app.providers.registry import Registry
from app.repositories.db import Database


@pytest.fixture
def gw(tmp_path, world):
    g = Gateway(Settings(), Database(str(tmp_path / "p.db")), ALL, transport=httpx.MockTransport(world.handler))

    async def no_sleep(_s):
        return None

    g.sleep = no_sleep
    return g


def test_catalog_is_complete_and_consistent():
    assert len(SPECS) >= 45 and len(HANDOFFS) >= 10
    for spec in SPECS:
        assert spec.docs.startswith("https://"), spec.id
        assert spec.capabilities and spec.timeout_s > 0 and spec.rate_per_min > 0
        if spec.access == "write":
            assert spec.env, f"{spec.id}: write providers must require credentials"
    assert all(h.access == "handoff" and h.homepage.startswith("https://") for h in HANDOFFS)
    assert {"openai", "anthropic", "gemini", "openrouter", "groq", "ollama"} <= {s.id for s in SPECS if s.access == "llm"}


async def test_unconfigured_provider_fails_closed_without_network(gw, world):
    with pytest.raises(ProviderError) as e:
        await gw.get("ticketmaster", "https://app.ticketmaster.com/discovery/v2/events.json")
    assert e.value.kind == "config" and "TICKETMASTER_API_KEY" in str(e.value) and world.calls == []


async def test_reads_retry_with_backoff_then_succeed(gw, world):
    world.fail["api.tvmaze.com"], world.fail_times["api.tvmaze.com"] = 503, 2
    data = await gw.get("tvmaze", "https://api.tvmaze.com/search/shows", params={"q": "x"})
    assert data and world.hits("api.tvmaze.com") == 3
    row = gw.db.one("SELECT retries, ok FROM provider_calls WHERE provider='tvmaze'")
    assert row == {"retries": 2, "ok": 1}


async def test_reads_are_cached(gw, world):
    for _ in range(3):
        await gw.get("tvmaze", "https://api.tvmaze.com/search/shows", params={"q": "x"})
    assert world.hits("api.tvmaze.com") == 1
    assert gw.db.one("SELECT SUM(cached) n FROM provider_calls")["n"] == 2


async def test_writes_are_never_retried_and_timeouts_are_ambiguous(gw, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "t")
    world.fail["api.x.com"] = "timeout"
    with pytest.raises(ProviderError) as e:
        await gw.post("x", "https://api.x.com/2/tweets", json={"text": "hi"})
    assert e.value.kind == "timeout" and e.value.sent is True
    assert world.hits("api.x.com") == 1


async def test_connect_error_is_not_ambiguous(gw, world, monkeypatch):
    monkeypatch.setenv("X_USER_ACCESS_TOKEN", "t")
    world.fail["api.x.com"] = "connect"
    with pytest.raises(ProviderError) as e:
        await gw.post("x", "https://api.x.com/2/tweets", json={"text": "hi"})
    assert e.value.sent is False


async def test_circuit_breaker_opens_and_isolates_one_provider(gw, world):
    world.fail["api.tvmaze.com"] = 500
    for _ in range(4):
        with pytest.raises(ProviderError):
            await gw.get("tvmaze", "https://api.tvmaze.com/shows/1", cache=False)
    before = world.hits("api.tvmaze.com")
    with pytest.raises(ProviderError) as e:
        await gw.get("tvmaze", "https://api.tvmaze.com/shows/1", cache=False)
    assert e.value.kind == "circuit_open" and world.hits("api.tvmaze.com") == before
    assert await gw.get("openlibrary", "https://openlibrary.org/search.json", params={"q": "x"})


async def test_host_allowlist_blocks_unexpected_hosts(gw):
    with pytest.raises(ValueError):
        await gw.get("tvmaze", "https://attacker.example/shows/1")
    with pytest.raises(ValueError):
        await gw.get("tvmaze", "http://api.tvmaze.com/shows/1")


@pytest.mark.parametrize("status,kind", [(401, "auth"), (429, "rate_limit"), (404, "bad_response")])
async def test_error_classification(gw, world, status, kind):
    world.fail["api.tvmaze.com"] = status
    with pytest.raises(ProviderError) as e:
        await gw.get("tvmaze", "https://api.tvmaze.com/shows/1")
    assert e.value.kind == kind and world.hits("api.tvmaze.com") == 1


async def test_registry_status_requires_a_real_probe(gw, world, monkeypatch):
    reg = Registry(gw, gw.db)
    assert reg.describe(ALL["tmdb"])["status"] == Status.CONFIG_REQUIRED.value
    assert reg.describe(ALL["zomato"])["status"] == Status.HANDOFF.value
    assert reg.describe(ALL["tvmaze"])["status"] == Status.UNVERIFIED.value
    assert (await reg.verify("tvmaze"))["status"] == Status.CONNECTED.value
    monkeypatch.setenv("TMDB_READ_TOKEN", "expired")
    assert reg.describe(ALL["tmdb"])["status"] == Status.UNVERIFIED.value  # a key alone is not "connected"
    world.fail["api.themoviedb.org"] = 401
    assert (await reg.verify("tmdb"))["status"] == Status.AUTH_EXPIRED.value
    world.fail["api.tvmaze.com"] = 429
    assert (await reg.verify("tvmaze"))["status"] == Status.RATE_LIMITED.value


async def test_registry_never_exposes_credential_values(gw, monkeypatch):
    monkeypatch.setenv("TMDB_READ_TOKEN", "super-secret-value")
    assert "super-secret-value" not in str(Registry(gw, gw.db).list())


async def test_model_router_strategies_fallback_and_measured_cost(gw, world, monkeypatch):
    router = ModelRouter(gw, gw.db)
    with pytest.raises(LLMUnavailable):
        await router.complete("composer", "s", "u")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert router.candidates("composer", "cost")[0].provider == "openai" and router.candidates("composer", "cost")[0].name == "gpt-4.1-nano"
    assert router.candidates("composer", "latency")[0].tier == "fast"
    assert router.candidates("critic", "balanced", exclude_provider="openai")[0].provider == "groq"
    world.fail["api.openai.com"] = 500
    r = await router.complete("composer", "s", "u sk-abcdefghijklmnopqrstuvwxyz123456", strategy="latency")
    assert r.provider == "groq" and r.prompt_tokens == 120 and r.completion_tokens == 30 and r.cost_usd > 0
    rows = gw.db.all("SELECT provider, ok, cost_usd FROM llm_calls ORDER BY id")
    assert [(x["provider"], x["ok"]) for x in rows] == [("openai", 0), ("groq", 1)] and rows[0]["cost_usd"] == 0

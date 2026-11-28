"""Provider abstraction: specifications, connection status, resilient async HTTP gateway and usage telemetry."""
from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from app.config import Settings, cred
from app.repositories.db import Database, now
from app.security import assert_public_https


class Status(str, Enum):
    CONNECTED = "connected_verified"
    CONFIG_REQUIRED = "configuration_required"
    AUTH_EXPIRED = "authentication_expired"
    UNAVAILABLE = "temporarily_unavailable"
    RATE_LIMITED = "rate_limited"
    HANDOFF = "external_handoff"
    UNVERIFIED = "configured_unverified"


class ProviderError(Exception):
    """Classified provider failure. `kind` is one of: config, auth, rate_limit, timeout, unavailable, bad_response, circuit_open."""

    def __init__(self, provider: str, kind: str, message: str, http_status: int | None = None, sent: bool = False):
        super().__init__(message)
        self.provider, self.kind, self.http_status, self.sent = provider, kind, http_status, sent

    def public(self) -> dict:
        return {"provider": self.provider, "error_class": self.kind, "message": str(self), "http_status": self.http_status}


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    name: str
    category: str
    capabilities: tuple[str, ...]
    hosts: tuple[str, ...] = ()
    env: tuple[str, ...] = ()
    access: str = "read"  # read | write | handoff | llm
    docs: str = ""
    attribution: str = ""
    rate_per_min: int = 60
    timeout_s: float = 10.0
    retries: int = 2
    concurrency: int = 4
    cache_ttl_s: int = 300
    scopes: tuple[str, ...] = ()
    response_schema: str = "Card[]"
    homepage: str = ""

    @property
    def configured(self) -> bool:
        return all(cred(k) for k in self.env)


@dataclass
class Breaker:
    failures: int = 0
    opened_at: float = 0.0
    threshold: int = 4
    cooldown_s: float = 30.0

    def allow(self) -> bool:
        return self.failures < self.threshold or time.monotonic() - self.opened_at > self.cooldown_s

    def success(self) -> None:
        self.failures = 0

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()

    @property
    def open(self) -> bool:
        return not self.allow()


@dataclass
class _State:
    breaker: Breaker = field(default_factory=Breaker)
    semaphore: asyncio.Semaphore | None = None
    window: list = field(default_factory=list)
    last_error: str = ""
    last_error_at: float = 0.0


class Gateway:
    """Single entry point for all provider HTTP traffic.

    Pooled async client, per-provider bounded concurrency and rate limits, TTL response cache for reads,
    exponential backoff with jitter (idempotent reads only), circuit breakers, host allowlists and telemetry.
    Writes are never retried: a transport failure after the request left the process is reported as `sent=True`
    so the caller can record the outcome as unknown.
    """

    def __init__(self, settings: Settings, db: Database | None, specs: dict[str, ProviderSpec], transport: httpx.AsyncBaseTransport | None = None):
        self.settings, self.db, self.specs = settings, db, specs
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._states: dict[str, _State] = {}
        self._cache: dict[str, tuple[float, Any]] = {}
        self.sleep: Callable[[float], Awaitable[None]] = asyncio.sleep

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                transport=self._transport,
                follow_redirects=False,
                limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
                headers={"User-Agent": self.settings.user_agent, "Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def state(self, provider: str) -> _State:
        st = self._states.setdefault(provider, _State())
        if st.semaphore is None:
            st.semaphore = asyncio.Semaphore(self.specs[provider].concurrency)
        return st

    def require(self, provider: str) -> ProviderSpec:
        spec = self.specs[provider]
        if not spec.configured:
            missing = [k for k in spec.env if not cred(k)]
            raise ProviderError(provider, "config", f"{spec.name} is not configured. Missing: {', '.join(missing)}")
        return spec

    def _record(self, provider, capability, ok, kind, status, latency, retries, cached):
        if self.db is None:
            return
        try:
            self.db.run(
                "INSERT INTO provider_calls(provider,capability,ok,error_class,http_status,latency_ms,retries,cached,created) VALUES(?,?,?,?,?,?,?,?,?)",
                (provider, capability, int(ok), kind, status, round(latency, 1), retries, int(cached), now()),
            )
        except Exception:  # telemetry must never break a request
            pass

    async def request(self, provider: str, method: str, url: str, *, capability: str = "", cache: bool | None = None,
                      expect: str = "json", **kwargs) -> Any:
        spec = self.require(provider)
        assert_public_https(url, spec.hosts or None)
        st = self.state(provider)
        is_read = method.upper() == "GET" or kwargs.pop("idempotent", False)
        use_cache = is_read if cache is None else cache
        key = f"{provider}|{method}|{url}|{sorted((kwargs.get('params') or {}).items())}|{kwargs.get('json')}" if use_cache else ""
        if key and key in self._cache and self._cache[key][0] > time.monotonic():
            self._record(provider, capability, True, "", 200, 0.0, 0, True)
            return self._cache[key][1]
        if not st.breaker.allow():
            self._record(provider, capability, False, "circuit_open", None, 0.0, 0, False)
            raise ProviderError(provider, "circuit_open", f"{spec.name} is temporarily paused after repeated failures")
        t = time.monotonic()
        st.window = [x for x in st.window if t - x < 60]
        if len(st.window) >= spec.rate_per_min:
            self._record(provider, capability, False, "rate_limit", None, 0.0, 0, False)
            raise ProviderError(provider, "rate_limit", f"Local rate limit for {spec.name} reached; try again shortly")
        attempts = (spec.retries if is_read else 0) + 1
        error: ProviderError | None = None
        started = time.monotonic()
        for attempt in range(attempts):
            st.window.append(time.monotonic())
            try:
                async with st.semaphore:
                    r = await self.client.request(method, url, timeout=spec.timeout_s, **kwargs)
            except httpx.TimeoutException:
                error = ProviderError(provider, "timeout", f"{spec.name} did not respond within {spec.timeout_s:.0f}s", sent=True)
            except httpx.HTTPError as exc:
                error = ProviderError(provider, "unavailable", f"{spec.name} could not be reached ({type(exc).__name__})", sent=not isinstance(exc, httpx.ConnectError))
            else:
                if 200 <= r.status_code < 300:
                    try:
                        data = (r.json() if r.content else {}) if expect == "json" else r
                    except ValueError:
                        error = ProviderError(provider, "bad_response", f"{spec.name} returned a non-JSON response", r.status_code, sent=True)
                    else:
                        st.breaker.success()
                        if key:
                            self._cache[key] = (time.monotonic() + spec.cache_ttl_s, data)
                            if len(self._cache) > 600:
                                for k in list(self._cache)[:200]:
                                    self._cache.pop(k, None)
                        self._record(provider, capability, True, "", r.status_code, (time.monotonic() - started) * 1000, attempt, False)
                        return data
                elif r.status_code in (401, 403):
                    error = ProviderError(provider, "auth", f"{spec.name} rejected the credentials (HTTP {r.status_code})", r.status_code)
                elif r.status_code == 429:
                    error = ProviderError(provider, "rate_limit", f"{spec.name} rate limit reached (HTTP 429)", 429)
                elif r.status_code >= 500:
                    error = ProviderError(provider, "unavailable", f"{spec.name} is unavailable (HTTP {r.status_code})", r.status_code, sent=True)
                else:
                    error = ProviderError(provider, "bad_response", f"{spec.name} rejected the request (HTTP {r.status_code})", r.status_code)
            if error.kind in ("timeout", "unavailable") and attempt + 1 < attempts:
                await self.sleep(min(4.0, 0.4 * 2 ** attempt) + random.uniform(0, 0.25))
                continue
            break
        assert error is not None
        if error.kind in ("timeout", "unavailable"):
            st.breaker.failure()
        st.last_error, st.last_error_at = error.kind, now()
        self._record(provider, capability, False, error.kind, error.http_status, (time.monotonic() - started) * 1000, attempt, False)
        raise error

    async def get(self, provider: str, url: str, **kw) -> Any:
        return await self.request(provider, "GET", url, **kw)

    async def post(self, provider: str, url: str, **kw) -> Any:
        return await self.request(provider, "POST", url, **kw)

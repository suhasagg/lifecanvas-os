"""Multi-provider model router with strategies, fallback, circuit breakers and measured usage accounting.

When no model provider is configured the router raises `LLMUnavailable`; agents then use their deterministic
rule-based path and say so in the trace. Nothing here ever fabricates a model response, token count or cost.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.config import cred
from app.providers.base import Gateway, ProviderError
from app.repositories.db import Database, now
from app.security import redact


class LLMUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Model:
    provider: str
    name: str
    tier: str  # quality | balanced | fast
    usd_in: float  # USD per million input tokens (list price; override with LIFECANVAS_PRICES)
    usd_out: float


CATALOG: list[Model] = [
    Model("anthropic", "claude-sonnet-4-5", "quality", 3.0, 15.0), Model("anthropic", "claude-haiku-4-5", "fast", 1.0, 5.0),
    Model("openai", "gpt-4.1", "quality", 2.0, 8.0), Model("openai", "gpt-4.1-mini", "balanced", 0.4, 1.6), Model("openai", "gpt-4.1-nano", "fast", 0.1, 0.4),
    Model("gemini", "gemini-2.5-pro", "quality", 1.25, 10.0), Model("gemini", "gemini-2.5-flash", "balanced", 0.3, 2.5),
    Model("openrouter", "openai/gpt-4.1-mini", "balanced", 0.4, 1.6), Model("groq", "llama-3.3-70b-versatile", "fast", 0.59, 0.79),
    Model("ollama", os.getenv("OLLAMA_MODEL", "llama3.1"), "balanced", 0.0, 0.0),
]
STRATEGIES = {
    "balanced": lambda m: ({"balanced": 0, "quality": 1, "fast": 2}[m.tier], m.usd_in + m.usd_out),
    "quality": lambda m: ({"quality": 0, "balanced": 1, "fast": 2}[m.tier], -(m.usd_in + m.usd_out)),
    "cost": lambda m: (m.usd_in + m.usd_out, 0),
    "latency": lambda m: ({"fast": 0, "balanced": 1, "quality": 2}[m.tier], m.usd_in + m.usd_out),
}
# Per-agent requirement overrides the session strategy where the role demands it.
AGENT_STRATEGY = {"planner": "quality", "critic": "quality", "creative": "quality", "router": "latency", "extractor": "cost"}


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: float
    parsed: BaseModel | None = None


class ModelRouter:
    def __init__(self, gateway: Gateway, db: Database | None):
        self.gw, self.db = gateway, db

    def available(self) -> list[Model]:
        return [m for m in CATALOG if self.gw.specs[m.provider].configured]

    def candidates(self, agent: str, strategy: str, exclude_provider: str = "") -> list[Model]:
        strategy = AGENT_STRATEGY.get(agent, strategy) if strategy == "balanced" else strategy
        models = sorted(self.available(), key=STRATEGIES.get(strategy, STRATEGIES["balanced"]))
        if exclude_provider:  # independent critic: prefer a different provider than the author
            models = [m for m in models if m.provider != exclude_provider] + [m for m in models if m.provider == exclude_provider]
        seen, out = set(), []
        for m in models:  # one model per provider in the fallback chain
            if m.provider not in seen and not self.gw.state(m.provider).breaker.open:
                seen.add(m.provider)
                out.append(m)
        return out

    def describe(self, strategy: str = "balanced") -> dict:
        return {"configured": sorted({m.provider for m in self.available()}), "strategy": strategy,
                "routes": {a: [f"{m.provider}/{m.name}" for m in self.candidates(a, strategy)] for a in ("planner", "specialist", "critic", "creative", "composer")},
                "catalog": [m.__dict__ | {"configured": self.gw.specs[m.provider].configured} for m in CATALOG]}

    async def complete(self, agent: str, system: str, user: str, *, schema: type[BaseModel] | None = None, strategy: str = "balanced",
                       user_id: str = "", run_id: str = "", max_tokens: int = 900, exclude_provider: str = "") -> LLMResult:
        chain = self.candidates(agent, strategy, exclude_provider)
        if not chain:
            raise LLMUnavailable("No language model provider is configured")
        user = redact(user)
        if schema is not None:
            system += "\nRespond with a single JSON object matching this JSON Schema and nothing else:\n" + json.dumps(schema.model_json_schema())
        last = ""
        for model in chain:
            started = time.monotonic()
            try:
                text, p_tok, c_tok = await self._call(model, system, user, max_tokens, json_mode=schema is not None)
                parsed = None
                if schema is not None:
                    match = re.search(r"\{.*\}", text, re.S)
                    parsed = schema.model_validate_json(match.group(0) if match else text)
            except (ProviderError, ValidationError, KeyError, IndexError, TypeError, ValueError) as exc:
                last = f"{model.provider}: {type(exc).__name__}"
                self._log(user_id, run_id, agent, model, 0, 0, 0.0, (time.monotonic() - started) * 1000, False, last)
                continue
            cost = round((p_tok * model.usd_in + c_tok * model.usd_out) / 1_000_000, 6)
            latency = (time.monotonic() - started) * 1000
            self._log(user_id, run_id, agent, model, p_tok, c_tok, cost, latency, True, "")
            return LLMResult(text, model.provider, model.name, p_tok, c_tok, cost, latency, parsed)
        raise LLMUnavailable(f"All configured model providers failed ({last})")

    async def _call(self, m: Model, system: str, user: str, max_tokens: int, json_mode: bool) -> tuple[str, int, int]:
        name = os.getenv(f"{m.provider.upper()}_MODEL", m.name)
        if m.provider == "anthropic":
            d = await self.gw.post("anthropic", "https://api.anthropic.com/v1/messages", cache=False, capability="chat",
                                   headers={"x-api-key": cred("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"},
                                   json={"model": name, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]})
            return "".join(b.get("text", "") for b in d["content"]), d["usage"]["input_tokens"], d["usage"]["output_tokens"]
        if m.provider == "gemini":
            cfg = {"maxOutputTokens": max_tokens} | ({"responseMimeType": "application/json"} if json_mode else {})
            d = await self.gw.post("gemini", f"https://generativelanguage.googleapis.com/v1beta/models/{name}:generateContent", cache=False, capability="chat",
                                   headers={"x-goog-api-key": cred("GEMINI_API_KEY")},
                                   json={"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": cfg})
            usage = d.get("usageMetadata", {})
            return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]), usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)
        url, key = {"openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"), "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
                    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"), "ollama": (cred("OLLAMA_BASE_URL").rstrip("/") + "/v1/chat/completions", "")}[m.provider]
        body = {"model": name, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if m.provider == "ollama":  # operator-configured local endpoint; plain HTTP on loopback is permitted for it only
            r = await self.gw.client.post(url, json=body, timeout=self.gw.specs["ollama"].timeout_s)
            r.raise_for_status()
            d = r.json()
        else:
            d = await self.gw.post(m.provider, url, cache=False, capability="chat", headers={"Authorization": "Bearer " + cred(key)}, json=body)
        usage = d.get("usage", {})
        return d["choices"][0]["message"]["content"] or "", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    def _log(self, user_id, run_id, agent, m, p, c, cost, latency, ok, error):
        if self.db is not None:
            self.db.run("INSERT INTO llm_calls(user_id,run_id,agent,provider,model,prompt_tokens,completion_tokens,cost_usd,latency_ms,ok,error,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (user_id, run_id, agent, m.provider, m.name, p, c, cost, round(latency, 1), int(ok), error, now()))

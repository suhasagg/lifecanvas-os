"""Runtime configuration. Secrets are read from the environment only and never persisted."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def cred(name: str) -> str:
    """Return a configured credential or an empty string. Never log the value."""
    return os.getenv(name, "").strip()


def has(*names: str) -> bool:
    return all(cred(n) for n in names)


@dataclass(frozen=True)
class Settings:
    db_path: str = "data/lifecanvas.sqlite3"
    checkpoint_path: str = "data/checkpoints.sqlite3"
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    allowed_origins: tuple[str, ...] = ()
    session_ttl_s: int = 14 * 24 * 3600
    approval_ttl_s: int = 900
    rate_limit_per_min: int = 240
    routing_strategy: str = "balanced"
    max_revisions: int = 1
    tool_deadline_s: float = 14.0
    secure_cookies: bool = False
    user_agent: str = "LifeCanvasOS/1.0 (+https://github.com/suhasagg/lifecanvas-os)"
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        split = lambda v: tuple(x.strip() for x in v.split(",") if x.strip())
        return cls(
            db_path=os.getenv("LIFECANVAS_DB", cls.db_path),
            checkpoint_path=os.getenv("LIFECANVAS_CHECKPOINTS", cls.checkpoint_path),
            allowed_hosts=split(os.getenv("LIFECANVAS_ALLOWED_HOSTS", ",".join(cls.allowed_hosts))),
            allowed_origins=split(os.getenv("LIFECANVAS_ALLOWED_ORIGINS", "")),
            session_ttl_s=int(os.getenv("LIFECANVAS_SESSION_TTL", cls.session_ttl_s)),
            approval_ttl_s=int(os.getenv("LIFECANVAS_APPROVAL_TTL", cls.approval_ttl_s)),
            rate_limit_per_min=int(os.getenv("LIFECANVAS_RATE_LIMIT", cls.rate_limit_per_min)),
            routing_strategy=os.getenv("LIFECANVAS_ROUTING", cls.routing_strategy),
            max_revisions=int(os.getenv("LIFECANVAS_MAX_REVISIONS", cls.max_revisions)),
            tool_deadline_s=float(os.getenv("LIFECANVAS_TOOL_DEADLINE", cls.tool_deadline_s)),
            secure_cookies=os.getenv("LIFECANVAS_SECURE_COOKIES", "0") == "1",
        )

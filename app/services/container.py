"""Service container shared by graphs, runtime and API."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.memory import Memory
from app.providers.base import Gateway
from app.providers.llm import ModelRouter
from app.providers.registry import Registry
from app.repositories.db import Database
from app.security import Audit
from app.services.community import Community
from app.tools.registry import ToolContext


@dataclass
class Services:
    settings: Settings
    db: Database
    gateway: Gateway
    registry: Registry
    router: ModelRouter
    memory: Memory
    audit: Audit
    community: Community
    actions: Any = None
    extras: dict = field(default_factory=dict)

    def tool_ctx(self, user_id: str, run_id: str) -> ToolContext:
        return ToolContext(self.gateway, self.db, user_id, run_id, self.community, self.settings.tool_deadline_s)

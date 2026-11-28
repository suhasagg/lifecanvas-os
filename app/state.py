"""Typed LangGraph state for the supervisor and specialist subgraphs."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field

SPECIALISTS = ("entertainment", "dining", "travel", "community", "culture", "research", "creative")
Specialist = Literal["entertainment", "dining", "travel", "community", "culture", "research", "creative"]


def merge_results(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer for parallel specialist reports: last write per task id wins, so revisions replace earlier output."""
    if right and right[0].get("__reset__"):
        return []
    merged = {r["task_id"]: r for r in left}
    merged.update({r["task_id"]: r for r in right})
    return list(merged.values())


def cap_trace(left: list[dict], right: list[dict]) -> list[dict]:
    return (left + right)[-400:]


class Task(BaseModel):
    """One unit of delegated work."""
    id: str
    specialist: Specialist
    objective: str = Field(max_length=300)
    query: str = Field(default="", max_length=160)
    params: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """Supervisor plan: independent tasks that run in parallel."""
    intent: str = Field(max_length=200)
    tasks: list[Task] = Field(max_length=7)
    wants_external_action: bool = False
    rationale: str = Field(default="", max_length=400)


class Verdict(BaseModel):
    """Independent critic verdict."""
    approved: bool
    score: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list, max_length=8)
    retry_tasks: list[str] = Field(default_factory=list, max_length=7)


class Draft(BaseModel):
    title: str = Field(max_length=160)
    body: str = Field(max_length=6000)


class SupervisorState(TypedDict, total=False):
    user_id: str
    thread_id: str
    run_id: str
    goal: str
    city: str
    country: str
    workflow: str
    strategy: str
    memories: list[dict]
    preferences: dict
    history: list[dict]
    security: dict
    understanding: dict
    plan: dict
    results: Annotated[list[dict], merge_results]
    trace: Annotated[list[dict], cap_trace]
    critique: dict
    revision: int
    proposals: list[dict]
    batch_id: str
    decisions: dict
    receipts: list[dict]
    answer: dict
    learned: list[dict]
    status: str


class SpecialistState(TypedDict, total=False):
    user_id: str
    run_id: str
    task: dict
    city: str
    country: str
    preferences: dict
    strategy: str
    place: dict
    queue: list[dict]
    tried: Annotated[list[str], operator.add]
    observations: Annotated[list[dict], operator.add]
    notices: Annotated[list[dict], operator.add]
    iteration: int
    cards: list[dict]
    extra: dict
    results: Annotated[list[dict], merge_results]
    trace: Annotated[list[dict], cap_trace]


class SpecialistOutput(TypedDict, total=False):
    results: Annotated[list[dict], merge_results]
    trace: Annotated[list[dict], cap_trace]


class ActionState(TypedDict, total=False):
    user_id: str
    run_id: str
    proposals: list[dict]
    batch_id: str
    decisions: dict
    receipts: list[dict]
    trace: Annotated[list[dict], cap_trace]


class ActionOutput(TypedDict, total=False):
    batch_id: str
    decisions: dict
    receipts: list[dict]
    trace: Annotated[list[dict], cap_trace]


def step(node: str, summary: str, **detail) -> dict:
    import time
    return {"node": node, "summary": summary, "at": time.time(), **({"detail": detail} if detail else {})}

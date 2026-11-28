"""Run lifecycle: start, stream, interrupt/resume, cancel and restart recovery on top of persistent checkpoints.

Each run is one LangGraph thread (thread_id == run_id) in the SQLite checkpointer, and every run row is owned by a
user; all lookups are scoped by user id. Events are persisted, so streams can be replayed after a reconnect.
"""
from __future__ import annotations

import asyncio
import uuid

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from app import supervisor
from app.repositories.db import dumps, loads, now
from app.security import clean_text
from app.services.container import Services
from app.subgraphs import action

RUN_DEADLINE_S = 150
ACTIVE = ("running", "awaiting_approval")


class RunError(Exception):
    pass


class Runtime:
    def __init__(self, svc: Services):
        self.svc, self.db = svc, svc.db
        self.tasks: dict[str, asyncio.Task] = {}
        self.conn = None
        self.graph = self.action_graph = self.checkpointer = None

    async def start(self) -> dict:
        path = self.svc.settings.checkpoint_path
        self.conn = await aiosqlite.connect(path)
        self.checkpointer = AsyncSqliteSaver(self.conn)
        await self.checkpointer.setup()
        self.graph = supervisor.build(self.svc, self.checkpointer)
        self.action_graph = action.build(self.svc, self.checkpointer)
        return self.recover()

    async def stop(self) -> None:
        for t in list(self.tasks.values()):
            t.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        if self.conn is not None:
            await self.conn.close()

    def recover(self) -> dict:
        """Runs that were mid-flight when the process stopped keep their last checkpoint and can be resumed."""
        n = self.db.run("UPDATE runs SET status='interrupted', updated=? WHERE status='running'", (now(),))
        for r in self.db.all("SELECT id,user_id FROM runs WHERE status='interrupted'") if n else []:
            self._emit(r["id"], r["user_id"], "status", "runtime", {"status": "interrupted", "note": "The service restarted. Resume to continue from the last checkpoint."})
        return {"interrupted_runs": n, "unknown_actions": self.svc.actions.recover()}

    # ---------------------------------------------------------------- events
    def _emit(self, run_id: str, user_id: str, kind: str, node: str, payload: dict) -> None:
        self.db.run("INSERT INTO run_events(run_id,user_id,kind,node,payload,created) VALUES(?,?,?,?,?,?)", (run_id, user_id, kind, node, dumps(payload), now()))

    def events(self, user_id: str, run_id: str, after: int = 0) -> list[dict]:
        rows = self.db.all("SELECT seq,kind,node,payload,created FROM run_events WHERE run_id=? AND user_id=? AND seq>? ORDER BY seq LIMIT 500", (run_id, user_id, after))
        for r in rows:
            r["payload"] = loads(r["payload"], {})
        return rows

    def _set(self, run_id: str, status: str, result: dict | None = None) -> None:
        if result is None:
            self.db.run("UPDATE runs SET status=?, updated=? WHERE id=?", (status, now(), run_id))
        else:
            self.db.run("UPDATE runs SET status=?, result=?, updated=? WHERE id=?", (status, dumps(result), now(), run_id))

    # ---------------------------------------------------------------- runs
    def get(self, user_id: str, run_id: str) -> dict:
        r = self.db.one("SELECT * FROM runs WHERE id=? AND user_id=?", (run_id, user_id))
        if not r:
            raise RunError("Run not found")
        r["result"] = loads(r["result"], None)
        return r

    def list(self, user_id: str, limit: int = 30) -> list[dict]:
        return self.db.all("SELECT id,thread_id,goal,city,workflow,strategy,status,created,updated FROM runs WHERE user_id=? ORDER BY created DESC LIMIT ?", (user_id, limit))

    async def forget(self, thread_ids: list[str]) -> None:
        """Delete saved checkpoints for these graph threads (used when an account is erased)."""
        for tid in thread_ids:
            if tid and self.checkpointer:
                await self.checkpointer.adelete_thread(tid)

    def submit(self, user_id: str, goal: str, city: str = "", country: str = "", workflow: str = "auto", strategy: str = "", thread_id: str = "") -> dict:
        goal = clean_text(goal, 1200)
        if not goal:
            raise RunError("Tell me what you would like to find, plan or create")
        if workflow not in supervisor.WORKFLOWS:
            raise RunError("Unknown workflow")
        if self.db.one("SELECT COUNT(*) n FROM runs WHERE user_id=? AND status='running'", (user_id,))["n"] >= 3:
            raise RunError("Three runs are already in progress; wait for one to finish or cancel it")
        if thread_id and not self.db.one("SELECT 1 x FROM threads WHERE id=? AND user_id=?", (thread_id, user_id)):
            thread_id = ""  # never attach to another user's conversation
        run_id, thread_id = uuid.uuid4().hex, thread_id or uuid.uuid4().hex
        strategy = strategy if strategy in ("balanced", "quality", "cost", "latency") else self.svc.settings.routing_strategy
        state = {"user_id": user_id, "thread_id": thread_id, "run_id": run_id, "goal": goal, "city": clean_text(city, 60), "country": clean_text(country, 2).upper(), "workflow": workflow, "strategy": strategy}
        self.db.run("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (run_id, user_id, thread_id, goal, state["city"], state["country"], workflow, strategy, "running", "null", now(), now()))
        self.svc.audit.record(user_id, "run.started", {"run": run_id, "workflow": workflow})
        self._spawn(run_id, user_id, state)
        return {"run_id": run_id, "thread_id": thread_id, "status": "running"}

    def _spawn(self, run_id: str, user_id: str, graph_input) -> None:
        task = asyncio.create_task(self._drive(run_id, user_id, graph_input))
        self.tasks[run_id] = task
        task.add_done_callback(lambda _t: self.tasks.pop(run_id, None))

    async def _drive(self, run_id: str, user_id: str, graph_input) -> None:
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 60}
        seen: set = set()
        try:
            async with asyncio.timeout(RUN_DEADLINE_S):
                async for ns, chunk in self.graph.astream(graph_input, config, stream_mode="updates", subgraphs=True):
                    for node, update in chunk.items():
                        if node == "__interrupt__":
                            continue
                        path = "/".join([p.split(":")[0] for p in ns] + [node])
                        for t in (update or {}).get("trace", []) if isinstance(update, dict) else []:
                            key = (t["node"], t["at"])
                            if key not in seen:  # subgraph steps surface again in the parent's update
                                seen.add(key)
                                self._emit(run_id, user_id, "step", t["node"], {"summary": t["summary"], "detail": t.get("detail", {}), "path": path, "at": t["at"]})
            snapshot = await self.graph.aget_state(config, subgraphs=True)
            pending = [i.value for t in snapshot.tasks for i in t.interrupts]
            values = snapshot.values
            if pending:
                answer = (values.get("answer") or {}) | {"batch_id": pending[0].get("batch_id", "")}
                self._set(run_id, "awaiting_approval", answer)
                self._emit(run_id, user_id, "interrupt", "action/gate", pending[0])
                self._emit(run_id, user_id, "status", "runtime", {"status": "awaiting_approval"})
            else:
                status = values.get("status", "completed")
                self._set(run_id, status, values.get("answer") or {})
                self._emit(run_id, user_id, "final", "runtime", {"status": status})
        except asyncio.CancelledError:
            self._set(run_id, "cancelled")
            self._emit(run_id, user_id, "status", "runtime", {"status": "cancelled", "note": "Cancelled. Completed steps stay in the checkpoint; nothing further will run."})
            self.svc.audit.record(user_id, "run.cancelled", {"run": run_id})
        except TimeoutError:
            self._set(run_id, "interrupted")
            self._emit(run_id, user_id, "status", "runtime", {"status": "interrupted", "note": f"The run exceeded its {RUN_DEADLINE_S}s deadline. Resume to continue from the last checkpoint."})
        except Exception as exc:  # noqa: BLE001 - surface a classified failure; details stay in server logs
            self._set(run_id, "failed", {"headline": "This run failed", "summary": f"An internal error stopped the run ({type(exc).__name__}). No external action was taken. You can resume from the last checkpoint.", "sections": []})
            self._emit(run_id, user_id, "status", "runtime", {"status": "failed", "error": type(exc).__name__})
            self.svc.audit.record(user_id, "run.failed", {"run": run_id, "error": type(exc).__name__})

    def cancel(self, user_id: str, run_id: str) -> dict:
        run = self.get(user_id, run_id)
        task = self.tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            return {"run_id": run_id, "status": "cancelling"}
        if run["status"] in ACTIVE:
            self._set(run_id, "cancelled")
            self.db.run("UPDATE actions SET status='rejected', decided=? WHERE run_id=? AND user_id=? AND status='pending'", (now(), run_id, user_id))
            self._emit(run_id, user_id, "status", "runtime", {"status": "cancelled"})
        return {"run_id": run_id, "status": "cancelled"}

    def resume(self, user_id: str, run_id: str, decision: dict | None = None) -> dict:
        """Resume from the last checkpoint: with a human decision (approval interrupt) or without (restart/deadline recovery)."""
        run = self.get(user_id, run_id)
        if run_id in self.tasks:
            raise RunError("This run is already executing")
        if decision is not None:
            if run["status"] != "awaiting_approval":
                raise RunError("This run is not waiting for approval")
            graph_input = Command(resume=decision)
        else:
            if run["status"] not in ("interrupted", "failed", "cancelled"):
                raise RunError(f"Only interrupted, failed or cancelled runs can be resumed (status: {run['status']})")
            graph_input = None
        self._set(run_id, "running")
        self._emit(run_id, user_id, "status", "runtime", {"status": "running", "note": "Resumed from checkpoint"})
        self.svc.audit.record(user_id, "run.resumed", {"run": run_id, "with_decision": decision is not None})
        self._spawn(run_id, user_id, graph_input)
        return {"run_id": run_id, "status": "running"}

    async def checkpoints(self, user_id: str, run_id: str) -> list[dict]:
        self.get(user_id, run_id)
        out = []
        async for snap in self.graph.aget_state_history({"configurable": {"thread_id": run_id}}, limit=40):
            out.append({"checkpoint_id": snap.config["configurable"].get("checkpoint_id"), "step": (snap.metadata or {}).get("step"), "source": (snap.metadata or {}).get("source"),
                        "next": list(snap.next), "created": snap.created_at, "interrupts": sum(len(t.interrupts) for t in snap.tasks)})
        return out

    # ---------------------------------------------------------------- direct action batches (Action Center, Creator Studio)
    async def propose(self, user_id: str, items: list[dict]) -> dict:
        batch_id = uuid.uuid4().hex
        thread = "act-" + batch_id
        out = await self.action_graph.ainvoke({"user_id": user_id, "run_id": thread, "proposals": items, "batch_id": batch_id}, {"configurable": {"thread_id": thread}})
        return {"batch_id": batch_id, "actions": self.svc.actions.list(user_id, batch_id), "rejected": (out.get("decisions") or {}).get("rejected_at_validation", []), "awaiting_approval": "__interrupt__" in out}

    async def decide(self, user_id: str, batch_id: str, approve: list[dict], reject: list[str]) -> dict:
        rows = self.svc.actions.list(user_id, batch_id)
        if not rows:
            raise RunError("Approval batch not found")
        owner, decision = rows[0]["run_id"], {"approve": approve, "reject": reject}
        if owner.startswith("act-"):
            config = {"configurable": {"thread_id": owner}}
            snap = await self.action_graph.aget_state(config)
            if not any(t.interrupts for t in snap.tasks):
                raise RunError("This batch is not waiting for a decision")
            await self.action_graph.ainvoke(Command(resume=decision), config)
            return {"batch_id": batch_id, "actions": self.svc.actions.list(user_id, batch_id)}
        self.resume(user_id, owner, decision)
        task = self.tasks.get(owner)
        if task:
            await asyncio.wait({task}, timeout=60)
        return {"batch_id": batch_id, "run_id": owner, "actions": self.svc.actions.list(user_id, batch_id)}

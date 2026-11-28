"""Action execution graph — the only place transactional tools are reachable.

    prepare -> gate (interrupt: human approval) -> decide -> execute -> verify -+-> END
                 ^--------------------------------------------------------------+  (undecided, unexpired items)

`gate` suspends the graph with `interrupt()`. It resumes only via `Command(resume={"approve": [{id, digest}], "reject": [ids]})`.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.services.actions import ActionError
from app.services.container import Services
from app.state import ActionOutput, ActionState, step


def build(svc: Services, checkpointer=None):
    actions = svc.actions

    async def prepare(s: ActionState) -> dict:
        out = actions.propose(s["user_id"], s.get("proposals", []), run_id=s.get("run_id", ""), batch_id=s.get("batch_id", ""))
        return {"batch_id": out["batch_id"], "receipts": [], "decisions": {"rejected_at_validation": out["rejected"]},
                "trace": [step("action.prepare", f"{len(out['actions'])} action(s) validated and persisted for approval" + (f"; {len(out['rejected'])} refused" if out["rejected"] else ""), batch=out["batch_id"])]}

    async def gate(s: ActionState) -> dict:
        pending = [a for a in actions.list(s["user_id"], s["batch_id"]) if a["status"] == "pending"]
        if not pending:
            return {"decisions": (s.get("decisions") or {}) | {"approve": [], "reject": []}}
        decision = interrupt({"type": "approval_required", "batch_id": s["batch_id"],
                              "actions": [{k: a[k] for k in ("id", "kind", "platform", "summary", "digest", "risk", "destination", "visibility", "expires", "depends_on", "connected")} for a in pending]})
        decision = decision if isinstance(decision, dict) else {}
        return {"decisions": (s.get("decisions") or {}) | {"approve": list(decision.get("approve", []))[:12], "reject": list(decision.get("reject", []))[:12]},
                "trace": [step("action.gate", f"Human decision received: {len(decision.get('approve', []))} approved, {len(decision.get('reject', []))} rejected")]}

    async def decide(s: ActionState) -> dict:
        d, notes = s.get("decisions") or {}, []
        batch_ids = {a["id"] for a in actions.list(s["user_id"], s["batch_id"])}
        for item in d.get("approve", []):
            aid, digest = (item.get("id"), item.get("digest", "")) if isinstance(item, dict) else (item, "")
            if aid not in batch_ids:
                notes.append(f"{str(aid)[:8]}: not part of this batch")
                continue
            try:
                actions.decide(s["user_id"], aid, True, digest)
            except ActionError as exc:
                notes.append(f"{aid[:8]}: {exc}")
        for aid in d.get("reject", []):
            if aid in batch_ids:
                try:
                    actions.decide(s["user_id"], aid, False)
                except ActionError as exc:
                    notes.append(f"{aid[:8]}: {exc}")
        return {"trace": [step("action.decide", "Decisions recorded against payload digests" + (f"; {len(notes)} refused" if notes else ""), notes=notes)]}

    async def execute(s: ActionState) -> dict:
        trace, done = [], set()
        for _ in range(3):  # dependency order: repeat until no approved action makes progress
            progressed = False
            for a in actions.list(s["user_id"], s["batch_id"]):
                if a["status"] != "approved" or a["id"] in done:
                    continue
                try:
                    r = await actions.execute(s["user_id"], a["id"])
                except ActionError as exc:
                    trace.append(step("action.execute", f"{a['platform']}: {exc}"))
                    done.add(a["id"])
                    continue
                if r["status"] != "approved":
                    progressed = True
                    done.add(a["id"])
                    trace.append(step("action.execute", f"{a['platform']}: {r['status']}", action=a["id"]))
                elif r.get("note"):
                    trace.append(step("action.execute", f"{a['platform']}: {r['note']}", action=a["id"]))
                    if "dependency" not in r["note"]:
                        done.add(a["id"])
            if not progressed:
                break
        return {"trace": trace or [step("action.execute", "No approved actions to execute")]}

    async def verify(s: ActionState) -> dict:
        rows = actions.list(s["user_id"], s["batch_id"])
        receipts = [{"id": a["id"], "kind": a["kind"], "platform": a["platform"], "status": a["status"], "receipt": a["result"].get("receipt"), "url": a["result"].get("url", ""),
                     "note": a["result"].get("note") or a["result"].get("message", "") or (f"Held: {a['platform']} is not connected, so nothing was sent. Connect it, then run the approved action from the Action Center." if a["status"] == "approved" and not a["connected"] else "")} for a in rows]
        counts: dict[str, int] = {}
        for a in rows:
            counts[a["status"]] = counts.get(a["status"], 0) + 1
        return {"receipts": receipts, "trace": [step("action.verify", "Receipts persisted: " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())), counts=counts)]}

    def more(s: ActionState) -> str:
        return "gate" if any(a["status"] == "pending" for a in actions.list(s["user_id"], s["batch_id"])) else END

    g = StateGraph(ActionState, output_schema=ActionOutput)
    for name, fn in (("prepare", prepare), ("gate", gate), ("decide", decide), ("execute", execute), ("verify", verify)):
        g.add_node(name, fn)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "gate")
    g.add_edge("gate", "decide")
    g.add_edge("decide", "execute")
    g.add_edge("execute", "verify")
    g.add_conditional_edges("verify", more, {"gate": "gate", END: END})
    return g.compile(name="action_executor", checkpointer=checkpointer)

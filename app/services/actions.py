"""Approval ledger for external writes.

Guarantees:
* every external write is a persisted proposal bound to a SHA-256 digest of its exact payload;
* approval must present that digest (so what the user saw is what is sent) before expiry;
* state transitions are atomic compare-and-set updates, so an approval or execution cannot be replayed;
* an identical payload already executed (or in an unknown state) is refused as a duplicate;
* dependencies must have executed first;
* a transport failure after the request was sent is recorded as `unknown` and is never retried automatically.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import uuid

from app.config import cred
from app.integrations import publish
from app.providers.base import Gateway, ProviderError
from app.repositories.db import Database, dumps, loads, now
from app.security import Audit, redact, screen

RISK = {"amadeus_flight_order": "high", "gmail": "high", "x": "high", "linkedin": "high", "instagram": "high", "facebook": "high", "bluesky": "high", "mastodon": "high", "wordpress": "medium", "telegram": "medium", "discord": "medium",
        "slack": "medium", "google_calendar": "low", "google_tasks": "low", "todoist": "low", "ms_graph": "low", "notion": "low", "google_drive": "low", "spotify_playlist": "low"}
VISIBILITY = {"amadeus_flight_order": "Private booking", "x": "Public", "linkedin": "Public", "instagram": "Public", "facebook": "Public (Page)", "bluesky": "Public", "mastodon": "Public", "wordpress": "Draft or public, as stated", "telegram": "Configured chat",
              "discord": "Configured channel", "slack": "Stated channel", "gmail": "Recipient only", "google_calendar": "Private (your primary calendar)", "google_tasks": "Private", "todoist": "Private",
              "ms_graph": "Private", "notion": "Stated page", "google_drive": "Private (your Drive)", "spotify_playlist": "Private playlist"}
OPEN = ("pending", "approved", "executing")


class ActionError(Exception):
    pass


def digest_of(kind: str, payload: dict) -> str:
    return hashlib.sha256(f"{kind}\n{dumps(payload)}".encode()).hexdigest()


class Actions:
    def __init__(self, db: Database, gateway: Gateway, audit: Audit, ttl_s: int = 900):
        self.db, self.gw, self.audit, self.ttl = db, gateway, audit, ttl_s

    # ---- views
    def _view(self, r: dict) -> dict:
        spec = self.gw.specs.get(r["kind"])
        payload = loads(r["payload"], {})
        status = "expired" if r["status"] == "pending" and r["expires"] < now() else r["status"]
        return {"id": r["id"], "batch_id": r["batch_id"], "run_id": r["run_id"], "kind": r["kind"], "platform": spec.name if spec else r["kind"], "payload": payload, "digest": r["digest"], "status": status,
                "risk": r["risk"], "depends_on": loads(r["depends_on"], []), "summary": r["summary"], "created": r["created"], "expires": r["expires"], "decided": r["decided"], "result": loads(r["result"], {}),
                "destination": payload.get("to") or payload.get("channel") or payload.get("page_id") or (spec.name if spec else r["kind"]), "visibility": VISIBILITY.get(r["kind"], "Unknown"),
                "cost": f"{payload['total']:.2f} {payload['currency']} (cap {payload['max_total']:.2f})" if r["kind"] == "amadeus_flight_order" else "No charge by LifeCanvasOS; provider plan limits apply", "connected": bool(spec and spec.configured), "missing": [k for k in (spec.env if spec else ()) if not cred(k)],
                "when": payload.get("start") or "Immediately on approval"}

    def get(self, user_id: str, action_id: str) -> dict:
        r = self.db.one("SELECT * FROM actions WHERE id=? AND user_id=?", (action_id, user_id))
        if not r:
            raise ActionError("Action not found")
        return self._view(r)

    def list(self, user_id: str, batch_id: str = "", limit: int = 80) -> list[dict]:
        if batch_id:
            rows = self.db.all("SELECT * FROM actions WHERE user_id=? AND batch_id=? ORDER BY created, rowid", (user_id, batch_id))
        else:
            rows = self.db.all("SELECT * FROM actions WHERE user_id=? ORDER BY created DESC, rowid DESC LIMIT ?", (user_id, limit))
        return [self._view(r) for r in rows]

    def ledger(self, user_id: str, action_id: str) -> list[dict]:
        return self.db.all("SELECT state,detail,created FROM ledger WHERE user_id=? AND action_id=? ORDER BY seq", (user_id, action_id))

    def _log(self, c, user_id: str, action_id: str, state: str, detail: str = "") -> None:
        c.execute("INSERT INTO ledger(user_id,action_id,state,detail,created) VALUES(?,?,?,?,?)", (user_id, action_id, state, redact(detail)[:500], now()))

    # ---- propose
    def propose(self, user_id: str, items: list[dict], run_id: str = "", batch_id: str = "") -> dict:
        """Validate and persist proposals. `depends_on` entries are indexes into `items`. Invalid items are rejected, not altered."""
        batch_id = batch_id or uuid.uuid4().hex
        existing = self.list(user_id, batch_id)
        if existing:  # idempotent re-entry after a restart
            return {"batch_id": batch_id, "actions": existing, "rejected": []}
        ids = [uuid.uuid4().hex for _ in items]
        rejected, created = [], []
        with self.db.tx(immediate=True) as c:
            for i, item in enumerate(items[:12]):
                kind = item.get("kind", "")
                try:
                    if kind not in publish.EXTERNAL:
                        raise ValueError(f"Unsupported action kind: {kind}")
                    payload = publish.validate(kind, item.get("payload") or {})
                    if any(screen(v)["blocked"] for v in payload.values() if isinstance(v, str)):
                        raise ValueError("Payload contains instruction-like content and was refused")
                    deps = [ids[d] for d in item.get("depends_on", []) if isinstance(d, int) and 0 <= d < i and ids[d] in created]
                    if len(deps) != len(item.get("depends_on", [])):
                        raise ValueError("A dependency of this action was itself rejected")
                except ValueError as exc:
                    rejected.append({"index": i, "kind": kind, "reason": str(exc)})
                    continue
                digest = digest_of(kind, payload)
                idem = hashlib.sha256(f"{user_id}|{digest}".encode()).hexdigest()
                dup = c.execute("SELECT id,status FROM actions WHERE user_id=? AND idem_key=? AND (status IN ('executed','unknown','executing','approved') OR (status='pending' AND expires>?))", (user_id, idem, now())).fetchone()
                if dup:
                    rejected.append({"index": i, "kind": kind, "reason": f"Duplicate of action {dup['id'][:8]} ({dup['status']}); the same content will not be sent twice"})
                    continue
                c.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ids[i], user_id, run_id, batch_id, kind, dumps(payload), digest, secrets.token_hex(16), idem, "pending", RISK.get(kind, "medium"),
                                                                                           dumps(deps), redact(str(item.get("summary", "")))[:200], now(), now() + self.ttl, None, "{}"))
                self._log(c, user_id, ids[i], "proposed", f"digest {digest[:12]}")
                created.append(ids[i])
        self.audit.record(user_id, "action.proposed", {"batch": batch_id, "count": len(created), "rejected": len(rejected)})
        return {"batch_id": batch_id, "actions": self.list(user_id, batch_id), "rejected": rejected}

    # ---- decide
    def decide(self, user_id: str, action_id: str, approve: bool, digest: str = "") -> dict:
        refusal = ""
        with self.db.tx(immediate=True) as c:
            r = c.execute("SELECT * FROM actions WHERE id=? AND user_id=?", (action_id, user_id)).fetchone()
            if not r:
                raise ActionError("Action not found")
            if r["status"] != "pending":
                raise ActionError(f"Action was already decided ({r['status']}); a decision cannot be replayed")
            if r["expires"] < now():
                c.execute("UPDATE actions SET status='expired' WHERE id=? AND status='pending'", (action_id,))
                self._log(c, user_id, action_id, "expired")
                refusal = "Approval window expired; propose the action again"
            elif approve and not secrets.compare_digest(digest or "", r["digest"]):
                self._log(c, user_id, action_id, "digest_mismatch")
                refusal = "Payload digest mismatch; the reviewed content is not the stored content"
            else:
                status = "approved" if approve else "rejected"
                # single-use nonce: the compare-and-set on status consumes the approval
                if c.execute("UPDATE actions SET status=?, decided=?, nonce='' WHERE id=? AND status='pending'", (status, now(), action_id)).rowcount != 1:
                    raise ActionError("Action was decided concurrently")
                self._log(c, user_id, action_id, status)
        if refusal:  # raised after commit so the refusal itself stays in the ledger
            self.audit.record(user_id, "action.refused", {"action": action_id, "reason": refusal})
            raise ActionError(refusal)
        self.audit.record(user_id, f"action.{status}", {"action": action_id, "kind": r["kind"], "digest": r["digest"][:12]})
        return self.get(user_id, action_id)

    # ---- execute
    async def execute(self, user_id: str, action_id: str) -> dict:
        with self.db.tx(immediate=True) as c:
            r = c.execute("SELECT * FROM actions WHERE id=? AND user_id=?", (action_id, user_id)).fetchone()
            if not r:
                raise ActionError("Action not found")
            if r["status"] != "approved":
                raise ActionError(f"Only approved actions can run (status: {r['status']})")
            payload = loads(r["payload"], {})
            if digest_of(r["kind"], payload) != r["digest"]:
                c.execute("UPDATE actions SET status='failed', result=? WHERE id=?", (dumps({"error": "Stored payload no longer matches the approved digest"}), action_id))
                self._log(c, user_id, action_id, "tampered")
                raise ActionError("Stored payload no longer matches the approved digest")
            for dep in loads(r["depends_on"], []):
                d = c.execute("SELECT status FROM actions WHERE id=? AND user_id=?", (dep, user_id)).fetchone()
                if not d or d["status"] != "executed":
                    self._log(c, user_id, action_id, "dependency_wait", f"{dep[:8]} is {d['status'] if d else 'missing'}")
                    return self._view(dict(r)) | {"blocked_by": dep, "note": "Waiting for a dependency to execute first"}
            spec = self.gw.specs[r["kind"]]
            if not spec.configured:
                self._log(c, user_id, action_id, "connection_required", ", ".join(spec.env))
                return self._view(dict(r)) | {"note": f"{spec.name} is not connected; the approved action is held and nothing was sent"}
            if c.execute("UPDATE actions SET status='executing' WHERE id=? AND status='approved'", (action_id,)).rowcount != 1:
                raise ActionError("Action is already executing")
            self._log(c, user_id, action_id, "executing")
        try:
            receipt = await publish.execute(self.gw, r["kind"], payload, r["idem_key"])
            status, result = "executed", receipt | {"verified": bool(receipt.get("receipt"))}
        except ProviderError as exc:
            # `sent` means the request may have reached the provider: the outcome is unknown and must not be retried.
            status = "unknown" if exc.sent else "failed"
            result = exc.public() | {"note": "Outcome unknown: check the destination before proposing again. LifeCanvasOS will not retry." if exc.sent else "Nothing was sent."}
        except asyncio.CancelledError:
            # Cancelled mid-request: the provider may already have received it. Record that, then let the cancellation continue.
            note = {"error_class": "cancelled", "note": "The run was cancelled while this was being sent. Outcome unknown: check the destination before proposing again."}
            with self.db.tx(immediate=True) as c:
                c.execute("UPDATE actions SET status='unknown', result=? WHERE id=? AND status='executing'", (dumps(note), action_id))
                self._log(c, user_id, action_id, "unknown", "cancelled during execution")
            raise
        except Exception as exc:  # noqa: BLE001 - never leave an action stuck in `executing`
            status, result = "unknown", {"error_class": "internal", "message": type(exc).__name__, "note": "Outcome unknown: check the destination before proposing again."}
        with self.db.tx(immediate=True) as c:
            c.execute("UPDATE actions SET status=?, result=? WHERE id=? AND status='executing'", (status, dumps(result), action_id))
            self._log(c, user_id, action_id, status, dumps(result))
        self.audit.record(user_id, f"action.{status}", {"action": action_id, "kind": r["kind"]})
        return self.get(user_id, action_id)

    def recover(self) -> int:
        """After a restart, anything still `executing` has an unknown outcome. It is never re-sent."""
        rows = self.db.all("SELECT id,user_id FROM actions WHERE status='executing'")
        for r in rows:
            with self.db.tx(immediate=True) as c:
                c.execute("UPDATE actions SET status='unknown', result=? WHERE id=? AND status='executing'", (dumps({"note": "The service restarted during execution. Outcome unknown; verify at the destination."}), r["id"]))
                self._log(c, r["user_id"], r["id"], "unknown", "restart during execution")
        return len(rows)

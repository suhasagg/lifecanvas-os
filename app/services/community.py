"""Consent-based community: opt-in profiles, interest matching, city-level proximity, requests, block and report.

Privacy rules enforced here (not in the UI): only users who opted in and confirmed they are adults are discoverable;
only display name, city and interests are ever exposed; exact location, email and activity are never shared;
blocked users are invisible to each other in both directions.
"""
from __future__ import annotations

import uuid

from app.memory import cosine, embed, pack, unpack
from app.repositories.db import Database, dumps, loads, now
from app.security import clean_text, redact


class CommunityError(Exception):
    pass


class Community:
    def __init__(self, db: Database):
        self.db = db

    def profile(self, user_id: str) -> dict | None:
        r = self.db.one("SELECT user_id,display_name,city,interests,bio,discoverable,adult_confirmed,updated FROM profiles WHERE user_id=?", (user_id,))
        if r:
            r["interests"] = loads(r["interests"], [])
        return r

    def save_profile(self, user_id: str, display_name: str, city: str, interests: list[str], bio: str, discoverable: bool, adult_confirmed: bool) -> dict:
        interests = sorted({clean_text(i, 30).lower() for i in interests if clean_text(i, 30)})[:20]
        if discoverable and not adult_confirmed:
            raise CommunityError("You must confirm you are 18 or older to be discoverable")
        if discoverable and (not clean_text(display_name, 40) or not clean_text(city, 60) or not interests):
            raise CommunityError("A display name, city and at least one interest are required to be discoverable")
        self.db.run("INSERT OR REPLACE INTO profiles VALUES(?,?,?,?,?,?,?,?,?)",
                    (user_id, clean_text(display_name, 40), clean_text(city, 60), dumps(interests), redact(clean_text(bio, 280)), int(discoverable), int(adult_confirmed), pack(embed(" ".join(interests))), now()))
        return self.profile(user_id)

    def _blocked(self, a: str, b: str) -> bool:
        return bool(self.db.one("SELECT 1 x FROM blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)", (a, b, b, a)))

    def matches(self, user_id: str, interests: list[str] | None = None, city: str = "", limit: int = 12) -> list[dict]:
        me = self.profile(user_id)
        wanted = sorted({i.lower() for i in (interests or (me or {}).get("interests") or [])})
        city = (city or (me or {}).get("city") or "").strip().lower()
        if not wanted:
            return []
        q = embed(" ".join(wanted))
        out = []
        for r in self.db.all("SELECT user_id,display_name,city,interests,bio,embedding FROM profiles WHERE discoverable=1 AND adult_confirmed=1 AND user_id!=?", (user_id,)):
            if self._blocked(user_id, r["user_id"]):
                continue
            theirs = loads(r["interests"], [])
            shared = sorted(set(wanted) & set(theirs))
            sim = cosine(q, unpack(r["embedding"]))
            same_city = bool(city) and r["city"].strip().lower() == city
            score = round(0.55 * (len(shared) / max(1, len(set(wanted) | set(theirs)))) + 0.25 * max(0.0, sim) + (0.20 if same_city else 0.0), 3)
            if not shared and sim < 0.25:
                continue
            link = self.db.one("SELECT status FROM connections WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)", (user_id, r["user_id"], r["user_id"], user_id))
            out.append({"user_id": r["user_id"], "display_name": r["display_name"], "city": r["city"], "interests": theirs, "bio": r["bio"], "shared": shared, "same_city": same_city,
                        "score": score, "connection": (link or {}).get("status", "none")})
        return sorted(out, key=lambda m: -m["score"])[:limit]

    def request(self, sender: str, recipient: str, message: str = "") -> dict:
        if sender == recipient:
            raise CommunityError("You cannot connect with yourself")
        target = self.profile(recipient)
        if not target or not target["discoverable"] or self._blocked(sender, recipient):
            raise CommunityError("This member is not available")
        mine = self.profile(sender)
        if not mine or not mine["discoverable"]:
            raise CommunityError("Opt in to discovery before sending requests")
        if self.db.one("SELECT 1 x FROM connections WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)", (sender, recipient, recipient, sender)):
            raise CommunityError("A request already exists between you")
        if self.db.one("SELECT COUNT(*) n FROM connections WHERE sender=? AND created>?", (sender, now() - 86400))["n"] >= 20:
            raise CommunityError("Daily request limit reached")
        cid = uuid.uuid4().hex
        self.db.run("INSERT INTO connections VALUES(?,?,?,?,?,?)", (cid, sender, recipient, "pending", redact(clean_text(message, 280)), now()))
        return {"id": cid, "status": "pending"}

    def respond(self, user_id: str, connection_id: str, accept: bool) -> dict:
        status = "accepted" if accept else "declined"
        if not self.db.run("UPDATE connections SET status=? WHERE id=? AND recipient=? AND status='pending'", (status, connection_id, user_id)):
            raise CommunityError("No pending request with that id is addressed to you")
        return {"id": connection_id, "status": status}

    def connections(self, user_id: str) -> dict:
        rows = self.db.all("SELECT c.id,c.sender,c.recipient,c.status,c.message,c.created,p.display_name,p.city,p.interests FROM connections c "
                           "JOIN profiles p ON p.user_id=CASE WHEN c.sender=? THEN c.recipient ELSE c.sender END WHERE c.sender=? OR c.recipient=? ORDER BY c.created DESC", (user_id, user_id, user_id))
        out = {"incoming": [], "outgoing": [], "connected": []}
        for r in rows:
            other = r["recipient"] if r["sender"] == user_id else r["sender"]
            if self._blocked(user_id, other):
                continue
            item = {"id": r["id"], "user_id": other, "display_name": r["display_name"], "city": r["city"], "interests": loads(r["interests"], []), "status": r["status"], "message": r["message"], "created": r["created"]}
            if r["status"] == "accepted":
                out["connected"].append(item)
            elif r["status"] == "pending":
                out["incoming" if r["recipient"] == user_id else "outgoing"].append(item)
        return out

    def block(self, user_id: str, other: str) -> None:
        if user_id == other:
            raise CommunityError("You cannot block yourself")
        with self.db.tx() as c:
            c.execute("INSERT OR IGNORE INTO blocks VALUES(?,?,?)", (user_id, other, now()))
            c.execute("DELETE FROM connections WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)", (user_id, other, other, user_id))

    def unblock(self, user_id: str, other: str) -> None:
        self.db.run("DELETE FROM blocks WHERE blocker=? AND blocked=?", (user_id, other))

    def blocked(self, user_id: str) -> list[dict]:
        return self.db.all("SELECT b.blocked user_id, COALESCE(p.display_name,'Member') display_name, b.created FROM blocks b LEFT JOIN profiles p ON p.user_id=b.blocked WHERE b.blocker=?", (user_id,))

    def report(self, user_id: str, other: str, reason: str) -> dict:
        reason = redact(clean_text(reason, 400))
        if not reason:
            raise CommunityError("A reason is required")
        rid = uuid.uuid4().hex
        self.db.run("INSERT INTO reports VALUES(?,?,?,?,?)", (rid, user_id, other, reason, now()))
        self.block(user_id, other)
        return {"id": rid, "status": "received", "blocked": True}

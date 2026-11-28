"""Agent-to-agent meetup negotiation between connected members.

Each member's personal agent holds that member's private constraints (budget ceiling, free dates, interests,
dietary needs). Agents never exchange those values. For every candidate option an agent discloses only a
verdict: accept or decline, plus a coarse preference rank. The coordinator picks the option every agent accepts
with the best combined rank. The result is a proposal: each participant must confirm it themselves.
"""
from __future__ import annotations

import uuid

from app.repositories.db import Database, dumps, loads, now
from app.security import clean_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetups(id TEXT PRIMARY KEY, organiser TEXT, title TEXT, options TEXT, outcome TEXT, status TEXT, created REAL);
CREATE TABLE IF NOT EXISTS meetup_members(meetup_id TEXT, user_id TEXT, constraints TEXT, confirmed INTEGER DEFAULT 0, PRIMARY KEY(meetup_id, user_id));
"""


class SocialError(Exception):
    pass


def agent_verdict(constraints: dict, option: dict) -> dict:
    """One member's agent evaluates one option privately and returns only accept/decline and a 0-3 rank."""
    cost, cap = option.get("cost_per_person"), constraints.get("max_budget")
    if cap is not None and cost is not None and cost > cap:
        return {"accept": False, "rank": 0}
    dates = constraints.get("dates") or []
    if dates and option.get("date") and option["date"] not in dates:
        return {"accept": False, "rank": 0}
    diet = (constraints.get("diet") or "").lower()
    if diet and option.get("diets") is not None and diet not in [d.lower() for d in option["diets"]]:
        return {"accept": False, "rank": 0}
    liked = {i.lower() for i in constraints.get("interests") or []}
    overlap = len(liked & {t.lower() for t in option.get("tags") or []})
    return {"accept": True, "rank": min(3, overlap + (1 if cap is not None and cost is not None and cost <= cap * 0.6 else 0))}


class Social:
    def __init__(self, db: Database, community):
        self.db, self.community = db, community
        with db.tx() as c:
            for stmt in SCHEMA.strip().split(";\n"):
                if stmt.strip():
                    c.execute(stmt)

    def _connected(self, a: str, b: str) -> bool:
        return bool(self.db.one("SELECT 1 x FROM connections WHERE status='accepted' AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?))", (a, b, b, a))) and not self.community._blocked(a, b)

    def create(self, organiser: str, title: str, options: list[dict], invitees: list[str], constraints: dict) -> dict:
        if not 1 <= len(options) <= 12:
            raise SocialError("Provide between 1 and 12 options")
        invitees = list(dict.fromkeys(i for i in invitees if i != organiser))[:8]
        if not invitees or not all(self._connected(organiser, i) for i in invitees):
            raise SocialError("You can only plan with members you are connected to")
        clean = [{"id": f"o{i + 1}", "title": clean_text(o.get("title"), 120), "date": clean_text(o.get("date"), 10), "cost_per_person": o.get("cost_per_person") if isinstance(o.get("cost_per_person"), (int, float)) else None,
                  "currency": clean_text(o.get("currency"), 3), "tags": [clean_text(t, 30) for t in (o.get("tags") or [])][:8], "diets": o.get("diets") if isinstance(o.get("diets"), list) else None,
                  "url": clean_text(o.get("url"), 300)} for i, o in enumerate(options)]
        mid = uuid.uuid4().hex
        with self.db.tx(immediate=True) as c:
            c.execute("INSERT INTO meetups VALUES(?,?,?,?,?,?,?)", (mid, organiser, clean_text(title, 120) or "Meetup", dumps(clean), "{}", "collecting", now()))
            c.execute("INSERT INTO meetup_members VALUES(?,?,?,0)", (mid, organiser, dumps(constraints)))
            for i in invitees:
                c.execute("INSERT INTO meetup_members VALUES(?,?,?,0)", (mid, i, "null"))
        return self.view(organiser, mid)

    def _row(self, user_id: str, mid: str) -> dict:
        m = self.db.one("SELECT m.* FROM meetups m JOIN meetup_members mm ON mm.meetup_id=m.id WHERE m.id=? AND mm.user_id=?", (mid, user_id))
        if not m or self.db.one("SELECT 1 x FROM meetup_members mm JOIN blocks b ON (b.blocker=? AND b.blocked=mm.user_id) OR (b.blocked=? AND b.blocker=mm.user_id) WHERE mm.meetup_id=?", (user_id, user_id, mid)):
            raise SocialError("Meetup not found")  # a block between any two participants closes the meetup to both
        return m

    def set_constraints(self, user_id: str, mid: str, constraints: dict) -> dict:
        self._row(user_id, mid)
        self.db.run("UPDATE meetup_members SET constraints=?, confirmed=0 WHERE meetup_id=? AND user_id=?", (dumps(constraints), mid, user_id))
        return self.negotiate(user_id, mid)

    def negotiate(self, user_id: str, mid: str) -> dict:
        m = self._row(user_id, mid)
        members = self.db.all("SELECT user_id, constraints FROM meetup_members WHERE meetup_id=?", (mid,))
        waiting = [x["user_id"] for x in members if loads(x["constraints"]) is None]
        if waiting:
            self.db.run("UPDATE meetups SET status='collecting' WHERE id=?", (mid,))
            return self.view(user_id, mid)
        rounds = []
        for o in loads(m["options"], []):
            verdicts = [agent_verdict(loads(x["constraints"], {}), o) for x in members]
            rounds.append({"option": o["id"], "accepted_by": sum(v["accept"] for v in verdicts), "of": len(members), "all_accept": all(v["accept"] for v in verdicts), "combined_rank": sum(v["rank"] for v in verdicts)})
        agreed = sorted((r for r in rounds if r["all_accept"]), key=lambda r: -r["combined_rank"])
        outcome = {"rounds": rounds, "chosen": agreed[0]["option"] if agreed else None,
                   "explanation": "Every agent accepted this option and it had the highest combined preference." if agreed else "No option satisfies everyone. Add options or relax a constraint; agents do not reveal whose constraint failed."}
        self.db.run("UPDATE meetups SET outcome=?, status=? WHERE id=?", (dumps(outcome), "proposed" if agreed else "no_agreement", mid))
        self.db.run("UPDATE meetup_members SET confirmed=0 WHERE meetup_id=?", (mid,))
        return self.view(user_id, mid)

    def confirm(self, user_id: str, mid: str) -> dict:
        m = self._row(user_id, mid)
        if m["status"] not in ("proposed", "confirmed"):
            raise SocialError("There is no agreed option to confirm yet")
        self.db.run("UPDATE meetup_members SET confirmed=1 WHERE meetup_id=? AND user_id=?", (mid, user_id))
        if not self.db.one("SELECT COUNT(*) n FROM meetup_members WHERE meetup_id=? AND confirmed=0", (mid,))["n"]:
            self.db.run("UPDATE meetups SET status='confirmed' WHERE id=?", (mid,))
        return self.view(user_id, mid)

    def view(self, user_id: str, mid: str) -> dict:
        m = self._row(user_id, mid)
        members = self.db.all("SELECT mm.user_id, mm.constraints, mm.confirmed, COALESCE(p.display_name,'Member') name FROM meetup_members mm LEFT JOIN profiles p ON p.user_id=mm.user_id WHERE mm.meetup_id=?", (mid,))
        options, outcome = loads(m["options"], []), loads(m["outcome"], {})
        mine = next(x for x in members if x["user_id"] == user_id)
        return {"id": m["id"], "title": m["title"], "status": m["status"], "organiser": m["organiser"] == user_id, "options": options, "outcome": outcome,
                "chosen": next((o for o in options if o["id"] == outcome.get("chosen")), None), "my_constraints": loads(mine["constraints"]),  # other members' constraints are never returned
                "members": [{"user_id": x["user_id"], "name": x["name"], "ready": loads(x["constraints"]) is not None, "confirmed": bool(x["confirmed"])} for x in members],
                "video_call": self.call_link(user_id, mid) if m["status"] == "confirmed" else None}

    def list(self, user_id: str) -> list[dict]:
        out = []
        for r in self.db.all("SELECT m.id FROM meetups m JOIN meetup_members mm ON mm.meetup_id=m.id WHERE mm.user_id=? ORDER BY m.created DESC LIMIT 30", (user_id,)):
            try:
                out.append(self.view(user_id, r["id"]))
            except SocialError:
                continue
        return out

    def call_link(self, user_id: str, key: str) -> str:
        import hashlib
        return "https://meet.jit.si/LifeCanvas-" + hashlib.sha256(f"room|{key}".encode()).hexdigest()[:24]

    def call_with(self, user_id: str, other: str) -> dict:
        """Private video room for two connected members. The room name is unguessable and derived from the connection."""
        row = self.db.one("SELECT id FROM connections WHERE status='accepted' AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?))", (user_id, other, other, user_id))
        if not row or self.community._blocked(user_id, other):
            raise SocialError("Video calls are available only between connected members")
        return {"url": self.call_link(user_id, row["id"]), "provider": "Jitsi Meet", "note": "Opens a private room on meet.jit.si. Share nothing you would not share in person."}

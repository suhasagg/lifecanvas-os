"""Persistent six-layer memory with local vector retrieval.

Layers: working (per-run scratchpad), conversation (thread turns), episodic (past runs), semantic (verified facts
with sources), procedural (workflows that succeeded) and preferences (editable user profile).
Embeddings are deterministic hashed character n-gram vectors computed locally, so recall works offline and no
user text leaves the process. Secrets are redacted and instruction-like content is refused before storage.
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
import uuid

from app.repositories.db import Database, dumps, loads, now
from app.security import clean_text, redact, screen

LAYERS = ("working", "conversation", "episodic", "semantic", "procedural", "preferences")
DIM = 256
STOP = set("a an the and or of to in on for with my me i is are be this that it at from by as please find show get some any want would like can you".split())

PREFERENCE_RULES: list[tuple[str, re.Pattern]] = [
    ("cuisine", re.compile(r"\b(?:i (?:love|like|enjoy|prefer|crave)|favou?rite (?:cuisine|food)s? (?:is|are))\s+([a-z ,&-]{3,60}?)\s+(?:food|cuisine|restaurants?|dishes)\b", re.I)),
    ("artist", re.compile(r"\b(?:favou?rite (?:artist|band|singer|musician)s? (?:is|are)|i(?: really)? (?:love|like) listening to|i'?m a (?:big |huge )?fan of)\s+([\w .,&'-]{2,60}?)(?:\.\s+(?:I|My|We)\b|[!?;]|\.?$| and i\b)", re.I)),
    ("team", re.compile(r"\b(?:i support|my (?:favou?rite )?team is|i follow|i cheer for)\s+([\w .&'-]{2,40}?)(?:[.!?,;]|$)", re.I)),
    ("diet", re.compile(r"\bi(?:'m| am)\s+(?:a\s+)?(vegetarian|vegan|pescatarian|gluten[- ]free|jain|halal|kosher)\b", re.I)),
    ("budget", re.compile(r"\b(?:budget (?:is|of)|under|below|at most|up to)\s+((?:₹|rs\.?|inr|\$|usd|€|eur|£)\s?[\d,]+(?:k)?|[\d,]+\s?(?:₹|rs|inr|usd|dollars|rupees|eur|euros))", re.I)),
    ("travel_style", re.compile(r"\bi (?:love|like|prefer|enjoy)\s+((?:beach|mountain|hill|city|road|solo|slow|adventure|backpacking|luxury|heritage|wildlife)[a-z ]{0,20}?)\s*(?:trips?|travel|holidays?|escapes?|getaways?)\b", re.I)),
    ("home_city", re.compile(r"\b[Ii] (?:live|am based|stay) in\s+([A-Z][\w .'-]{2,40}?)(?:[.!?,;]|$)")),
]


def embed(text: str) -> list[float]:
    """Hashed bag of word unigrams and character trigrams, L2-normalised."""
    vec = [0.0] * DIM
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]
    feats = [(w, 1.0) for w in words] + [(w[i:i + 3], 0.5) for w in words for i in range(max(1, len(w) - 2))]
    for feat, weight in feats:
        h = int.from_bytes(hashlib.blake2b(feat.encode(), digest_size=8).digest(), "big")
        vec[h % DIM] += weight if (h >> 60) & 1 else -weight
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def pack(vec: list[float]) -> bytes:
    return struct.pack(f"{DIM}f", *vec)


def unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{DIM}f", blob))


class Memory:
    def __init__(self, db: Database):
        self.db = db

    # ---- writes
    def remember(self, user_id: str, layer: str, key: str, content: str, meta: dict | None = None) -> dict | None:
        if layer not in LAYERS:
            raise ValueError("Unknown memory layer")
        content = redact(clean_text(content, 1200))
        if not content or screen(content)["blocked"]:
            return None  # never persist instruction-like or empty content
        key = clean_text(key, 120)
        existing = self.db.one("SELECT id FROM memories WHERE user_id=? AND layer=? AND key=?", (user_id, layer, key)) if layer in ("preferences", "procedural", "working") else None
        mid = existing["id"] if existing else uuid.uuid4().hex
        self.db.run("INSERT OR REPLACE INTO memories(id,user_id,layer,key,content,meta,embedding,created,last_used,uses) VALUES(?,?,?,?,?,?,?,?,?,COALESCE((SELECT uses FROM memories WHERE id=?),0))",
                    (mid, user_id, layer, key, content, dumps(meta or {}), pack(embed(f"{key} {content}")), now(), now(), mid))
        return {"id": mid, "layer": layer, "key": key, "content": content}

    def learn_preferences(self, user_id: str, text: str) -> list[dict]:
        """Extract explicit first-person preference statements. Conservative by design: only stated facts are stored."""
        out = []
        for kind, pattern in PREFERENCE_RULES:
            for m in pattern.finditer(text):
                value = clean_text(m.group(1), 80).strip(" .,")
                if value and len(value) > 1:
                    item = self.remember(user_id, "preferences", f"{kind}:{value.lower()}", value, {"kind": kind, "source": "stated in conversation"})
                    if item:
                        out.append(item | {"kind": kind})
        return out

    def add_turn(self, user_id: str, thread_id: str, role: str, body: str, meta: dict | None = None) -> None:
        with self.db.tx() as c:
            if not c.execute("SELECT 1 FROM threads WHERE id=? AND user_id=?", (thread_id, user_id)).fetchone():
                c.execute("INSERT INTO threads VALUES(?,?,?,?,?)", (thread_id, user_id, clean_text(body, 70), now(), now()))
            c.execute("UPDATE threads SET updated=? WHERE id=?", (now(), thread_id))
            c.execute("INSERT INTO messages(user_id,thread_id,role,body,meta,created) VALUES(?,?,?,?,?,?)", (user_id, thread_id, role, redact(body)[:8000], dumps(meta or {}), now()))

    # ---- reads
    def conversation(self, user_id: str, thread_id: str, limit: int = 30) -> list[dict]:
        rows = self.db.all("SELECT role,body,meta,created FROM (SELECT * FROM messages WHERE user_id=? AND thread_id=? ORDER BY id DESC LIMIT ?) ORDER BY id", (user_id, thread_id, limit))
        for r in rows:
            r["meta"] = loads(r["meta"], {})
        return rows

    def threads(self, user_id: str) -> list[dict]:
        return self.db.all("SELECT id,title,created,updated FROM threads WHERE user_id=? ORDER BY updated DESC LIMIT 40", (user_id,))

    def preferences(self, user_id: str) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for r in self.db.all("SELECT content,meta FROM memories WHERE user_id=? AND layer='preferences' ORDER BY created", (user_id,)):
            out.setdefault(loads(r["meta"], {}).get("kind", "other"), []).append(r["content"])
        return out

    def recall(self, user_id: str, query: str, layers: tuple[str, ...] = ("episodic", "semantic", "procedural", "preferences"), k: int = 6, touch: bool = True) -> list[dict]:
        """Rank memories by cosine similarity blended with recency and reinforcement."""
        q = embed(query)
        rows = self.db.all(f"SELECT * FROM memories WHERE user_id=? AND layer IN ({','.join('?' * len(layers))})", (user_id, *layers))
        t, scored = now(), []
        for r in rows:
            sim = cosine(q, unpack(r["embedding"]))
            recency = math.exp(-(t - r["created"]) / (30 * 86400))
            score = 0.75 * sim + 0.15 * recency + 0.10 * min(1.0, r["uses"] / 5)
            if sim > 0.08:
                scored.append((score, sim, r))
        scored.sort(key=lambda x: -x[0])
        top = scored[:k]
        if touch and top:
            with self.db.tx() as c:
                for _, _, r in top:
                    c.execute("UPDATE memories SET uses=uses+1,last_used=? WHERE id=?", (t, r["id"]))
        return [{"id": r["id"], "layer": r["layer"], "key": r["key"], "content": r["content"], "meta": loads(r["meta"], {}), "score": round(s, 3), "similarity": round(sim, 3)} for s, sim, r in top]

    def inspect(self, user_id: str) -> dict:
        out = {layer: [] for layer in LAYERS}
        for r in self.db.all("SELECT id,layer,key,content,meta,created,last_used,uses FROM memories WHERE user_id=? ORDER BY created DESC LIMIT 400", (user_id,)):
            r["meta"] = loads(r["meta"], {})
            out[r["layer"]].append(r)
        out["conversation"] = [{"id": t["id"], "key": t["title"], "content": f"{self.db.one('SELECT COUNT(*) n FROM messages WHERE thread_id=? AND user_id=?', (t['id'], user_id))['n']} turns", "created": t["updated"], "meta": {"thread": True}} for t in self.threads(user_id)]
        return out

    def forget(self, user_id: str, memory_id: str | None = None, layer: str | None = None) -> int:
        if memory_id:
            n = self.db.run("DELETE FROM memories WHERE user_id=? AND id=?", (user_id, memory_id))
            if not n:  # conversation threads are addressed by thread id
                n = self.db.run("DELETE FROM messages WHERE user_id=? AND thread_id=?", (user_id, memory_id))
                self.db.run("DELETE FROM threads WHERE user_id=? AND id=?", (user_id, memory_id))
            return n
        if layer == "conversation":
            self.db.run("DELETE FROM threads WHERE user_id=?", (user_id,))
            return self.db.run("DELETE FROM messages WHERE user_id=?", (user_id,))
        if layer in LAYERS:
            return self.db.run("DELETE FROM memories WHERE user_id=? AND layer=?", (user_id, layer))
        raise ValueError("Specify a memory id or a layer")

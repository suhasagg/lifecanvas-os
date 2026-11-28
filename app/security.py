"""Security primitives: authentication, sentinel screening, redaction, SSRF guard, rate limiting, audit chain.

Pattern-based screening is a first line of defence only. The structural controls are what matter:
agents hold least-privilege tool allowlists, retrieved content is treated as data and never as
instructions, and every external write requires an approved, hash-bound action.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import ipaddress
import re
import secrets
import socket
import time
import uuid
from urllib.parse import urlsplit

from app.repositories.db import Database, dumps, loads, now

# ---------------------------------------------------------------- authentication
PBKDF_ROUNDS = 310_000
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,180}\.[A-Za-z]{2,}")


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF_ROUNDS)
    return f"pbkdf2${PBKDF_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
        probe = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(probe.hex(), digest)
    except (ValueError, AttributeError):
        return False


class Auth:
    def __init__(self, db: Database, ttl_s: int):
        self.db, self.ttl = db, ttl_s

    def register(self, email: str, name: str, password: str) -> dict:
        email = email.strip().lower()
        name = clean_text(name, 60)
        if not EMAIL_RE.fullmatch(email):
            raise ValueError("Enter a valid email address")
        if len(password) < 8:
            raise ValueError("Password must have at least 8 characters")
        if not name:
            raise ValueError("Name is required")
        uid = uuid.uuid4().hex
        try:
            self.db.run("INSERT INTO users VALUES(?,?,?,?,?)", (uid, email, name, hash_password(password), now()))
        except Exception:
            raise ValueError("An account with this email already exists") from None
        return {"id": uid, "email": email, "name": name}

    def login(self, email: str, password: str) -> dict:
        row = self.db.one("SELECT * FROM users WHERE email=?", (email.strip().lower(),))
        if not row or not verify_password(password, row["pw_hash"]):
            raise PermissionError("Invalid email or password")
        return {"id": row["id"], "email": row["email"], "name": row["name"]}

    def issue(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.db.run("INSERT INTO sessions VALUES(?,?,?,?)", (_sha(token), user_id, now(), now() + self.ttl))
        return token

    def resolve(self, token: str | None) -> dict | None:
        if not token:
            return None
        row = self.db.one(
            "SELECT u.id,u.email,u.name FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?",
            (_sha(token), now()),
        )
        return row

    def revoke(self, token: str | None) -> None:
        if token:
            self.db.run("DELETE FROM sessions WHERE token_hash=?", (_sha(token),))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------- redaction and cleaning
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}"
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}|Bearer\s+[A-Za-z0-9._~+/-]{16,})"
)
PHONE_RE = re.compile(r"(?<![\w.])\+?\d[\d\s().-]{8,16}\d(?![\w.])")
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
TAG_RE = re.compile(r"<[^>]{0,400}>")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")


def redact(text: str) -> str:
    """Remove secrets and personal identifiers before text reaches logs, audit records or model prompts."""
    text = SECRET_RE.sub("[redacted-secret]", str(text))
    text = EMAIL_RE.sub("[redacted-email]", text)
    text = CARD_RE.sub("[redacted-number]", text)
    return PHONE_RE.sub("[redacted-phone]", text)


def clean_text(value, limit: int = 600) -> str:
    """Normalise untrusted provider text: strip markup and control characters, collapse whitespace, bound length."""
    text = html.unescape(TAG_RE.sub(" ", str(value or "")))
    text = CONTROL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def safe_url(value) -> str:
    try:
        u = urlsplit(str(value or ""))
    except ValueError:
        return ""
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return ""
    return u.geturl()[:800]


# ---------------------------------------------------------------- sentinel
INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("override_instructions", re.compile(r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|system|safety)\b.{0,30}\b(instructions?|prompts?|rules?|polic(y|ies)|guardrails?)", re.I | re.S)),
    ("system_prompt_exfiltration", re.compile(r"\b(reveal|print|show|repeat|leak|dump|expose)\b.{0,40}\b(system prompt|hidden prompt|developer message|initial instructions)", re.I | re.S)),
    ("credential_exfiltration", re.compile(r"\b(reveal|print|show|send|leak|dump|exfiltrate|email|post)\b.{0,50}\b(api[_ -]?keys?|secrets?|passwords?|access tokens?|credentials|env(ironment)? variables?)", re.I | re.S)),
    ("role_hijack", re.compile(r"\b(you are now|act as|pretend to be|switch to)\b.{0,30}\b(dan|developer mode|jailbroken|unrestricted|root|admin)", re.I | re.S)),
    ("approval_bypass", re.compile(r"\b(without|skip|bypass|no need for|auto[- ]?approve)\b.{0,30}\b(approval|confirmation|consent|asking|review)", re.I | re.S)),
    ("tool_abuse", re.compile(r"\b(delete|wipe|drop)\b.{0,30}\b(all|every)\b.{0,30}\b(emails?|files?|events?|memor(y|ies)|data|accounts?)", re.I | re.S)),
    ("privacy_violation", re.compile(r"\b(find|get|scrape|track|locate)\b.{0,40}\b(home address|exact location|phone number|private (profile|contact|account))", re.I | re.S)),
    ("markup_injection", re.compile(r"<\s*(script|iframe|object|embed)\b|javascript:|data:text/html", re.I)),
]


def screen(text: str) -> dict:
    """Screen text for known prompt-injection and abuse patterns. Returns the matched rule names."""
    hits = [name for name, pattern in INJECTION_PATTERNS if pattern.search(text or "")]
    return {"blocked": bool(hits), "rules": hits}


def isolate(text: str) -> tuple[str, bool]:
    """Untrusted-content isolation: returns cleaned text and whether it carried instruction-like content.

    Flagged text is withheld from model prompts and from memory; the card itself stays visible to the user
    with its source link.
    """
    cleaned = clean_text(text)
    return cleaned, screen(cleaned)["blocked"]


# ---------------------------------------------------------------- SSRF guard
def assert_public_https(url: str, allowed_hosts: tuple[str, ...] | None = None, resolve: bool = False) -> str:
    u = urlsplit(url)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not host or u.username or u.password:
        raise ValueError("Only credential-free HTTPS URLs are allowed")
    if allowed_hosts is not None and not any(host == h or host.endswith("." + h) for h in allowed_hosts):
        raise ValueError(f"Host {host} is not on the provider allowlist")
    candidates = [host]
    if resolve:
        try:
            candidates = [info[4][0] for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)]
        except OSError:
            raise ValueError("Host could not be resolved") from None
    for item in candidates:
        try:
            ip = ipaddress.ip_address(item)
        except ValueError:
            if item in ("localhost",) or item.endswith((".local", ".internal", ".localhost")):
                raise ValueError("Private hosts are not allowed") from None
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError("Private network addresses are not allowed")
    return url


# ---------------------------------------------------------------- rate limiting
class RateLimiter:
    """In-process sliding window limiter keyed by user or client address."""

    def __init__(self, per_minute: int):
        self.limit, self.hits = per_minute, {}

    def allow(self, key: str) -> bool:
        t = time.monotonic()
        window = [x for x in self.hits.get(key, ()) if t - x < 60]
        if len(window) >= self.limit:
            self.hits[key] = window
            return False
        window.append(t)
        self.hits[key] = window
        return True


# ---------------------------------------------------------------- tamper-evident audit log
class Audit:
    def __init__(self, db: Database):
        self.db = db

    def record(self, user_id: str | None, kind: str, detail: dict | None = None) -> str:
        body = redact(dumps(detail or {}))[:4000]
        with self.db.tx(immediate=True) as c:
            last = c.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
            prev = last["hash"] if last else "genesis"
            created = now()
            digest = hashlib.sha256(f"{prev}|{user_id}|{kind}|{body}|{created!r}".encode()).hexdigest()
            c.execute("INSERT INTO audit(user_id,kind,detail,prev_hash,hash,created) VALUES(?,?,?,?,?,?)", (user_id, kind, body, prev, digest, created))
        return digest

    def verify(self) -> dict:
        prev, count = "genesis", 0
        for r in self.db.all("SELECT * FROM audit ORDER BY seq"):
            expected = hashlib.sha256(f"{prev}|{r['user_id']}|{r['kind']}|{r['detail']}|{r['created']!r}".encode()).hexdigest()
            if r["prev_hash"] != prev or r["hash"] != expected:
                return {"verified": False, "count": count, "broken_at": r["seq"]}
            prev, count = r["hash"], count + 1
        return {"verified": True, "count": count, "head": prev}

    def entries(self, user_id: str, limit: int = 60) -> list[dict]:
        rows = self.db.all("SELECT seq,kind,detail,hash,created FROM audit WHERE user_id=? ORDER BY seq DESC LIMIT ?", (user_id, limit))
        for r in rows:
            r["detail"] = loads(r["detail"], {})
        return rows


def security_event(db: Database, user_id: str | None, kind: str, detail: dict) -> None:
    db.run("INSERT INTO security_events(user_id,kind,detail,created) VALUES(?,?,?,?)", (user_id, kind, redact(dumps(detail))[:2000], now()))

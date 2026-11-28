"""SQLite persistence. One short-lived connection per operation, WAL journal, user-scoped queries."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, pw_hash TEXT, created REAL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT, created REAL, expires REAL);
CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, user_id TEXT, title TEXT, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, thread_id TEXT, role TEXT, body TEXT, meta TEXT, created REAL);
CREATE INDEX IF NOT EXISTS ix_messages ON messages(user_id, thread_id, id);
CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, user_id TEXT, layer TEXT, key TEXT, content TEXT, meta TEXT, embedding BLOB, created REAL, last_used REAL, uses INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_memories ON memories(user_id, layer);
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, user_id TEXT, thread_id TEXT, goal TEXT, city TEXT, country TEXT, workflow TEXT, strategy TEXT, status TEXT, result TEXT, created REAL, updated REAL);
CREATE INDEX IF NOT EXISTS ix_runs ON runs(user_id, created);
CREATE TABLE IF NOT EXISTS run_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, user_id TEXT, kind TEXT, node TEXT, payload TEXT, created REAL);
CREATE INDEX IF NOT EXISTS ix_events ON run_events(run_id, seq);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, user_id TEXT, run_id TEXT, batch_id TEXT, kind TEXT, payload TEXT, digest TEXT, nonce TEXT, idem_key TEXT, status TEXT, risk TEXT, depends_on TEXT, summary TEXT, created REAL, expires REAL, decided REAL, result TEXT);
CREATE INDEX IF NOT EXISTS ix_actions ON actions(user_id, created);
CREATE INDEX IF NOT EXISTS ix_actions_idem ON actions(user_id, idem_key);
CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action_id TEXT, state TEXT, detail TEXT, created REAL);
CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, kind TEXT, detail TEXT, prev_hash TEXT, hash TEXT, created REAL);
CREATE TABLE IF NOT EXISTS profiles(user_id TEXT PRIMARY KEY, display_name TEXT, city TEXT, interests TEXT, bio TEXT, discoverable INTEGER, adult_confirmed INTEGER, embedding BLOB, updated REAL);
CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY, sender TEXT, recipient TEXT, status TEXT, message TEXT, created REAL, UNIQUE(sender, recipient));
CREATE TABLE IF NOT EXISTS blocks(blocker TEXT, blocked TEXT, created REAL, PRIMARY KEY(blocker, blocked));
CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, reporter TEXT, reported TEXT, reason TEXT, created REAL);
CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, title TEXT, data TEXT, starts TEXT, created REAL);
CREATE INDEX IF NOT EXISTS ix_plans ON plans(user_id, created);
CREATE TABLE IF NOT EXISTS provider_calls(id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, capability TEXT, ok INTEGER, error_class TEXT, http_status INTEGER, latency_ms REAL, retries INTEGER, cached INTEGER, created REAL);
CREATE INDEX IF NOT EXISTS ix_provider_calls ON provider_calls(provider, created);
CREATE TABLE IF NOT EXISTS provider_checks(provider TEXT PRIMARY KEY, ok INTEGER, error_class TEXT, detail TEXT, latency_ms REAL, checked REAL);
CREATE TABLE IF NOT EXISTS llm_calls(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, run_id TEXT, agent TEXT, provider TEXT, model TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd REAL, latency_ms REAL, ok INTEGER, error TEXT, created REAL);
CREATE TABLE IF NOT EXISTS tool_calls(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, user_id TEXT, agent TEXT, tool TEXT, provider TEXT, ok INTEGER, items INTEGER, latency_ms REAL, error TEXT, created REAL);
CREATE INDEX IF NOT EXISTS ix_tool_calls ON tool_calls(run_id);
CREATE TABLE IF NOT EXISTS security_events(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, kind TEXT, detail TEXT, created REAL);
"""


def now() -> float:
    return time.time()


class Database:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:" and os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        c = sqlite3.connect(self.path, timeout=15)
        try:
            c.executescript(SCHEMA)
        finally:
            c.close()

    @contextmanager
    def tx(self, immediate: bool = False):
        c = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=15000")
        try:
            c.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield c
            c.execute("COMMIT")
        except BaseException:
            try:
                c.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            c.close()

    def all(self, sql: str, args: tuple = ()) -> list[dict]:
        with self.tx() as c:
            return [dict(r) for r in c.execute(sql, args)]

    def one(self, sql: str, args: tuple = ()) -> dict | None:
        with self.tx() as c:
            r = c.execute(sql, args).fetchone()
            return dict(r) if r else None

    def run(self, sql: str, args: tuple = ()) -> int:
        with self.tx() as c:
            return c.execute(sql, args).rowcount


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def loads(value, default=None):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default

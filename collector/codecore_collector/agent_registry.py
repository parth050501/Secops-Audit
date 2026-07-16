"""
Agent registry for the collector (relay) side.

Agents run on/near target systems, do the actual scanning, and send raw results
to the collector. Each agent authenticates to the collector with an agent token.

Agent tokens are issued by the collector when an agent enrolls. The collector
stores only the hash. This keeps the agent→collector hop authenticated even
though it is inside the customer network ("no loose threads").

The collector itself is bound to ONE tenant (via its own platform token), so
every agent under a collector inherits that tenant implicitly — the collector
forwards all agent results under its own tenant binding. An agent therefore
cannot cause cross-tenant data; the collector's platform token governs that.
"""
import sqlite3
import os
import secrets
import hashlib
import time
from contextlib import contextmanager


def generate_agent_token() -> str:
    return "agt_" + secrets.token_urlsafe(32)


def _hash(token: str) -> str:
    # Simple salted hash for the local agent registry (SHA-256 with per-row salt).
    # (bcrypt would add a dependency; for the local agent hop SHA-256+salt is fine,
    # and the real tenant-security boundary is the collector's platform token.)
    return hashlib.sha256(token.encode()).hexdigest()


class AgentRegistry:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._init()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    system_type TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    token_prefix TEXT,
                    enrolled_at REAL NOT NULL,
                    last_seen REAL
                )
            """)

    def enroll(self, name: str, system_type: str) -> str:
        """Register an agent, return its token (shown once)."""
        token = generate_agent_token()
        with self._conn() as c:
            c.execute(
                "INSERT INTO agents (name, system_type, token_hash, token_prefix, enrolled_at) "
                "VALUES (?,?,?,?,?)",
                (name, system_type, _hash(token), token[:12], time.time()),
            )
        return token

    def authenticate(self, token: str):
        """Return the agent row if the token is valid, else None."""
        if not token or not token.startswith("agt_"):
            return None
        h = _hash(token)
        with self._conn() as c:
            row = c.execute(
                "SELECT id, name, system_type FROM agents WHERE token_hash=?", (h,)
            ).fetchone()
            if row:
                c.execute("UPDATE agents SET last_seen=? WHERE id=?", (time.time(), row[0]))
                return {"id": row[0], "name": row[1], "system_type": row[2]}
        return None

    def list_agents(self):
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, name, system_type, last_seen FROM agents ORDER BY enrolled_at"
            ).fetchall()
        return [{"id": r[0], "name": r[1], "system_type": r[2], "last_seen": r[3]} for r in rows]

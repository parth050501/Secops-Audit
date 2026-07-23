"""
Durable local result queue.

When a scan completes, its result is written here first, then uploaded. If the
APE is unreachable, results stay queued and are retried later — nothing is lost
if the network drops (customer networks are flaky; this is what makes the
collector production-grade rather than best-effort).
"""
import sqlite3
import os
import json
import time
from contextlib import contextmanager


class ResultQueue:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self._init()

    def _init(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    system_type TEXT NOT NULL,
                    target TEXT,
                    framework TEXT,
                    raw_data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    attempts INTEGER DEFAULT 0
                )
            """)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def enqueue(self, system_type, raw_data, job_id=None, target=None, framework=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO results (job_id, system_type, target, framework, raw_data, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (job_id, system_type, target, framework,
                 json.dumps(raw_data) if not isinstance(raw_data, str) else raw_data,
                 time.time()),
            )

    def pending(self, limit=20):
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, job_id, system_type, target, framework, raw_data, attempts "
                "FROM results ORDER BY created_at ASC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {"id": r[0], "job_id": r[1], "system_type": r[2], "target": r[3],
             "framework": r[4], "raw_data": r[5], "attempts": r[6]}
            for r in rows
        ]

    def mark_uploaded(self, row_id):
        with self._conn() as c:
            c.execute("DELETE FROM results WHERE id=?", (row_id,))

    def mark_failed(self, row_id):
        with self._conn() as c:
            c.execute("UPDATE results SET attempts = attempts + 1 WHERE id=?", (row_id,))

    def count(self):
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM results").fetchone()[0]

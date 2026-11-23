"""SQLite audit log of triage decisions (standard library only)."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS triage_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT    NOT NULL,
    customer_email TEXT    NOT NULL,
    subject        TEXT    NOT NULL,
    category       TEXT    NOT NULL,
    priority       TEXT    NOT NULL,
    assigned_queue TEXT    NOT NULL
)
"""


class TriageStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.getenv("TRIAGE_DB_PATH", "triage_history.db")
        with closing(self._connect()) as conn, conn:
            conn.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def record(self, customer_email: str, subject: str, category: str, priority: str, queue: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO triage_history (timestamp, customer_email, subject, category, priority, assigned_queue) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), customer_email, subject,
                 category, priority, queue),
            )

    def recent(self, limit: int = 20, priority: str | None = None) -> list[dict]:
        query = "SELECT * FROM triage_history"
        params: list = []
        if priority:
            query += " WHERE priority = ?"
            params.append(priority)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as conn:
            return [dict(row) for row in conn.execute(query, params)]

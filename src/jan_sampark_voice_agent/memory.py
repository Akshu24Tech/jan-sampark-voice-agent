"""Cross-call (long-term) memory: a tiny SQLite store keyed by citizen_id.

Within-call memory lives in ConversationState (schema.py). This persists the
FeedbackRecord so a callback resumes context ("Last time you mentioned X...").
Mirrors the STM + persistent-LTM split from the Voice-Enabled Chatbot project.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .schema import FeedbackRecord

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "citizens.db"


class CitizenMemory:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        # Explicit open/close (not `with connect()`), so the file handle is
        # released -- important on Windows where an open handle blocks deletes.
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        conn = self._conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    citizen_id TEXT PRIMARY KEY,
                    scheme     TEXT,
                    record     TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def load(self, citizen_id: str) -> Optional[FeedbackRecord]:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT record FROM feedback WHERE citizen_id = ?", (citizen_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return FeedbackRecord(**json.loads(row[0]))

    def save(self, record: FeedbackRecord) -> None:
        record.touch()
        conn = self._conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO feedback (citizen_id, scheme, record, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (record.citizen_id, record.scheme, record.model_dump_json(), record.updated_at),
            )
            conn.commit()
        finally:
            conn.close()

    def has_seen(self, citizen_id: str) -> bool:
        return self.load(citizen_id) is not None

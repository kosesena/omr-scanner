"""
Persistent storage for OMR Scanner using SQLite.
Saves sessions (answer keys, rosters, scan results) to a local database
so data survives server restarts.
"""

import sqlite3
import json
import os
from contextlib import contextmanager
from app.models import ExamSession

DB_DIR = os.environ.get("OMR_DATA_DIR", "/tmp/omr_data")
DB_PATH = os.path.join(DB_DIR, "omr_scanner.db")


def _ensure_dir():
    os.makedirs(DB_DIR, exist_ok=True)


@contextmanager
def _get_db():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_session(session: ExamSession):
    """Save or update a session in the database."""
    with _get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO sessions (session_id, data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session.session_id, session.model_dump_json()))


def load_all_sessions() -> dict[str, ExamSession]:
    """Load all sessions from database."""
    sessions = {}
    with _get_db() as conn:
        rows = conn.execute("SELECT session_id, data FROM sessions").fetchall()
    for sid, data in rows:
        try:
            sessions[sid] = ExamSession.model_validate_json(data)
        except Exception:
            pass  # Skip corrupted entries
    return sessions


def delete_session(session_id: str):
    """Delete a session from the database."""
    with _get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

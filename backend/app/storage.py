"""
Persistent storage for OMR Scanner using Supabase.
Falls back to SQLite if Supabase is not configured.
"""

import os
import json
import base64
import sqlite3
from contextlib import contextmanager
from app.models import ExamSession

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET_NAME = "form-images"

# SQLite fallback config
DB_DIR = os.environ.get("OMR_DATA_DIR", "/tmp/omr_data")
DB_PATH = os.path.join(DB_DIR, "omr_scanner.db")

# Supabase client singleton
_supabase_client = None


def _get_supabase():
    global _supabase_client
    if _supabase_client is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def _use_supabase():
    return bool(SUPABASE_URL and SUPABASE_KEY)


# =====================
# SQLite fallback
# =====================

@contextmanager
def _get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_sqlite():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _save_sqlite(session: ExamSession):
    with _get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (session.session_id, session.model_dump_json()),
        )


def _load_all_sqlite() -> dict[str, ExamSession]:
    sessions = {}
    with _get_db() as conn:
        rows = conn.execute("SELECT session_id, data FROM sessions").fetchall()
    for sid, data in rows:
        try:
            sessions[sid] = ExamSession.model_validate_json(data)
        except Exception:
            pass
    return sessions


def _delete_sqlite(session_id: str):
    with _get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


# =====================
# Supabase
# =====================

def _save_supabase(session: ExamSession):
    client = _get_supabase()
    # Strip base64 images before saving to DB (they're in storage)
    data = session.model_dump()
    for r in data.get("results", []):
        r.pop("form_image_base64", None)
    client.table("sessions").upsert({
        "session_id": session.session_id,
        "data": json.dumps(data),
    }).execute()


def _load_all_supabase() -> dict[str, ExamSession]:
    client = _get_supabase()
    sessions = {}
    try:
        result = client.table("sessions").select("session_id, data").execute()
        for row in result.data:
            try:
                data = row["data"]
                if isinstance(data, str):
                    data = json.loads(data)
                sessions[row["session_id"]] = ExamSession.model_validate(data)
            except Exception:
                pass
    except Exception as e:
        print(f"Supabase load error: {e}")
    return sessions


def _delete_supabase(session_id: str):
    client = _get_supabase()
    client.table("sessions").delete().eq("session_id", session_id).execute()
    # Delete all images for this session
    try:
        files = client.storage.from_(BUCKET_NAME).list(session_id)
        if files:
            paths = [f"{session_id}/{f['name']}" for f in files]
            if paths:
                client.storage.from_(BUCKET_NAME).remove(paths)
    except Exception as e:
        print(f"Storage cleanup error: {e}")


# =====================
# Image storage
# =====================

def upload_form_image(session_id: str, result_index: int, image_base64: str) -> str:
    """Upload form image to Supabase Storage. Returns public URL."""
    if not _use_supabase():
        return ""
    client = _get_supabase()
    path = f"{session_id}/{result_index}.jpg"
    image_bytes = base64.b64decode(image_base64)
    try:
        # Remove existing file first (in case of re-scan)
        try:
            client.storage.from_(BUCKET_NAME).remove([path])
        except Exception:
            pass
        client.storage.from_(BUCKET_NAME).upload(
            path, image_bytes, {"content-type": "image/jpeg"}
        )
    except Exception as e:
        print(f"Image upload error: {e}")
        return ""
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"


def get_form_image_url(session_id: str, result_index: int) -> str:
    """Get public URL for a form image."""
    if not _use_supabase():
        return ""
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{session_id}/{result_index}.jpg"


def delete_form_image(session_id: str, result_index: int):
    """Delete a single form image from storage."""
    if not _use_supabase():
        return
    client = _get_supabase()
    try:
        client.storage.from_(BUCKET_NAME).remove([f"{session_id}/{result_index}.jpg"])
    except Exception:
        pass


# =====================
# Public API
# =====================

def init_db():
    if _use_supabase():
        _get_supabase()  # Initialize client
        print("Using Supabase storage")
    else:
        _init_sqlite()
        print("Using SQLite fallback (no Supabase credentials)")


def save_session(session: ExamSession):
    if _use_supabase():
        _save_supabase(session)
    else:
        _save_sqlite(session)


def load_all_sessions() -> dict[str, ExamSession]:
    if _use_supabase():
        return _load_all_supabase()
    return _load_all_sqlite()


def delete_session(session_id: str):
    if _use_supabase():
        _delete_supabase(session_id)
    else:
        _delete_sqlite(session_id)

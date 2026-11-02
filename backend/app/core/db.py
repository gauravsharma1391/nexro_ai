"""SQLite storage. Every function lives here so a PostgreSQL version can replace this one module."""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def conn():
    c = sqlite3.connect(settings.db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS conversations(
            id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL, content TEXT NOT NULL, provider TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS datasets(
            id TEXT PRIMARY KEY, filename TEXT NOT NULL, rows INTEGER NOT NULL, cols INTEGER NOT NULL,
            parent_id TEXT, created_at TEXT NOT NULL);
        """)


def create_conversation(title: str) -> str:
    cid, now = uuid.uuid4().hex, _now()
    with conn() as c:
        c.execute("INSERT INTO conversations VALUES(?,?,?,?)", (cid, title[:80] or "New chat", now, now))
    return cid


def list_conversations(limit: int = 200) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS message_count "
            "FROM conversations c ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_conversation(cid: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None


def get_messages(cid: str) -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT role, content, provider, created_at FROM messages "
                         "WHERE conversation_id=? ORDER BY id", (cid,)).fetchall()
    return [dict(r) for r in rows]


def add_message(cid: str, role: str, content: str, provider: str | None = None) -> None:
    now = _now()
    with conn() as c:
        c.execute("INSERT INTO messages(conversation_id,role,content,provider,created_at) VALUES(?,?,?,?,?)",
                  (cid, role, content, provider, now))
        c.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))


def delete_last_assistant(cid: str) -> None:
    with conn() as c:
        r = c.execute("SELECT id, role FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1",
                      (cid,)).fetchone()
        if r and r["role"] == "assistant":
            c.execute("DELETE FROM messages WHERE id=?", (r["id"],))


def rename_conversation(cid: str, title: str) -> bool:
    with conn() as c:
        return c.execute("UPDATE conversations SET title=? WHERE id=?", (title[:80], cid)).rowcount > 0


def delete_conversation(cid: str) -> bool:
    with conn() as c:
        return c.execute("DELETE FROM conversations WHERE id=?", (cid,)).rowcount > 0


def record_dataset(did: str, filename: str, rows: int, cols: int, parent: str | None = None) -> None:
    with conn() as c:
        c.execute("INSERT INTO datasets VALUES(?,?,?,?,?,?)", (did, filename, rows, cols, parent, _now()))


def get_dataset(did: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM datasets WHERE id=?", (did,)).fetchone()
    return dict(r) if r else None


def list_datasets(limit: int = 50) -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM datasets ORDER BY created_at DESC LIMIT ?", (limit,))]


def stats() -> dict:
    with conn() as c:
        one = lambda q: c.execute(q).fetchone()[0]  # noqa: E731
        return {"conversations": one("SELECT COUNT(*) FROM conversations"),
                "messages": one("SELECT COUNT(*) FROM messages"),
                "user_messages": one("SELECT COUNT(*) FROM messages WHERE role='user'"),
                "datasets": one("SELECT COUNT(*) FROM datasets")}

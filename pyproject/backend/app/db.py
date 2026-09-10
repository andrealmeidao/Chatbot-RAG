import sqlite3
import threading
from uuid import uuid4

from app.config import DB_PATH

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                );
                """
            )
            conv_cols = _column_names(conn, "conversations")
            if "user_id" not in conv_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
            if "title" not in conv_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
            conn.commit()
        finally:
            conn.close()


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def create_user(username: str, password_hash: str) -> dict:
    user_id = str(uuid4())
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user_id, username, password_hash, now_iso()),
            )
            conn.commit()
        finally:
            conn.close()
    return {"id": user_id, "username": username}


def get_user_by_username(username: str) -> dict | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def create_session(token: str, user_id: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, now_iso()),
            )
            conn.commit()
        finally:
            conn.close()


def get_session(token: str) -> dict | None:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT s.token, s.user_id, u.username
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
        finally:
            conn.close()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()


def ensure_conversation(conversation_id: str | None, user_id: str, title: str | None = None) -> str:
    cid = conversation_id or str(uuid4())
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT id, user_id, title FROM conversations WHERE id = ?", (cid,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO conversations (id, created_at, user_id, title) VALUES (?, ?, ?, ?)",
                    (cid, now_iso(), user_id, title or "Nova conversa"),
                )
            else:
                owner = row["user_id"]
                if owner and owner != user_id:
                    raise PermissionError("Conversa de outro usuario")
                if not owner:
                    conn.execute("UPDATE conversations SET user_id = ? WHERE id = ?", (user_id, cid))
                if title and (not row["title"] or row["title"] == "Nova conversa"):
                    conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title[:80], cid))
            conn.commit()
        finally:
            conn.close()
    return cid


def list_conversations(user_id: str) -> list[dict]:
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT c.id, c.title, c.created_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS messages
                FROM conversations c
                WHERE c.user_id = ?
                ORDER BY c.created_at DESC
                """,
                (user_id,),
            ).fetchall()
        finally:
            conn.close()
    return [dict(row) for row in rows]


def save_message(conversation_id: str, question: str, answer: str, sources: str, confidence: float) -> str:
    message_id = str(uuid4())
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, question, answer, sources, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, conversation_id, question, answer, sources, confidence, now_iso()),
            )
            conn.execute(
                """
                UPDATE conversations
                SET title = CASE WHEN title IS NULL OR title = 'Nova conversa' THEN ? ELSE title END
                WHERE id = ?
                """,
                (question[:80], conversation_id),
            )
            conn.commit()
        finally:
            conn.close()
    return message_id


def get_history(conversation_id: str, user_id: str | None = None) -> list[dict]:
    with _lock:
        conn = _connect()
        try:
            if user_id:
                owned = conn.execute(
                    "SELECT id FROM conversations WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
                    (conversation_id, user_id),
                ).fetchone()
                if owned is None:
                    return []
            rows = conn.execute(
                """
                SELECT id, question, answer, sources, confidence, created_at
                FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
                """,
                (conversation_id,),
            ).fetchall()
        finally:
            conn.close()
    return [dict(row) for row in rows]


def save_feedback(message_id: str, rating: int, comment: str | None) -> str:
    feedback_id = str(uuid4())
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO feedback (id, message_id, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (feedback_id, message_id, rating, comment, now_iso()),
            )
            conn.commit()
        finally:
            conn.close()
    return feedback_id


def analytics(user_id: str | None = None) -> dict:
    with _lock:
        conn = _connect()
        try:
            if user_id:
                total = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE c.user_id = ?
                    """,
                    (user_id,),
                ).fetchone()["c"]
                top_questions = conn.execute(
                    """
                    SELECT m.question, COUNT(*) AS count
                    FROM messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE c.user_id = ?
                    GROUP BY m.question
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    (user_id,),
                ).fetchall()
            else:
                total = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
                top_questions = conn.execute(
                    """
                    SELECT question, COUNT(*) AS count
                    FROM messages
                    GROUP BY question
                    ORDER BY count DESC
                    LIMIT 10
                    """
                ).fetchall()
            feedback_counts = conn.execute(
                """
                SELECT rating, COUNT(*) AS count
                FROM feedback
                GROUP BY rating
                """
            ).fetchall()
        finally:
            conn.close()
    return {
        "total_questions": total,
        "top_questions": [dict(row) for row in top_questions],
        "feedback": {str(row["rating"]): row["count"] for row in feedback_counts},
    }

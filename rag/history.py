"""Persistence for per-student conversation history.

This module owns every direct interaction with the database that stores
students and their messages. It is intentionally standalone: no imports from
``rag/chain.py``, ``app/main.py``, or any other project module. Business logic
for the chat lives elsewhere; this layer only creates, reads, updates and
deletes rows.

The connection factory chooses Turso (libSQL) when ``TURSO_DATABASE_URL`` and
``TURSO_AUTH_TOKEN`` are both set, otherwise it falls back to local SQLite for
dev convenience. Schema and behavior are documented in
``openspec/changes/2026-08-14-persistent-history/design.md``.
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone

#: Environment variable that sets the SQLite file path. Falls back to the
#: project-default location used by ``app/main.py`` and documented in AGENTS.md.
_SQLITE_PATH_ENV = "SQLITE_PATH"
_DEFAULT_DB_PATH = "./data/historial.db"

#: Turso connection settings. When both are set, the backend uses libSQL.
_TURSO_URL_ENV = "TURSO_DATABASE_URL"
_TURSO_TOKEN_ENV = "TURSO_AUTH_TOKEN"

#: Roles supported by the ``messages`` table. Anything outside this set is
#: rejected by ``save_message`` to keep the prompt/history contract clean.
_VALID_ROLES = ("user", "assistant")

#: Cached connection, created lazily on first use and reused across requests.
_connection = None
_connection_lock = threading.Lock()


def _get_connection():
    """Return a cached DB connection (Turso if creds set, else local SQLite)."""
    global _connection
    if _connection is not None:
        return _connection

    with _connection_lock:
        if _connection is not None:
            return _connection

        url = os.getenv(_TURSO_URL_ENV)
        token = os.getenv(_TURSO_TOKEN_ENV)
        if url and token:
            import libsql_experimental as libsql

            _connection = libsql.connect(url, auth_token=token)
        else:
            db_path = os.getenv(_SQLITE_PATH_ENV, _DEFAULT_DB_PATH)
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            _connection = sqlite3.connect(db_path)
            _connection.execute("PRAGMA journal_mode = WAL")
            _connection.execute("PRAGMA foreign_keys = ON")
        return _connection


def _configure_connection(conn: sqlite3.Connection) -> None:
    """No-op shim kept for diff minimality.

    The local-SQLite branch in ``_get_connection`` already enables WAL mode and
    foreign keys. libSQL handles these internally, so no per-call setup is
    needed.
    """
    pass  # noqa: PIE970


def _utc_now() -> str:
    """Return the current UTC time as an ISO 8601 string with seconds."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rows_to_dicts(cursor) -> list[dict]:
    """Convert cursor results to dicts using cursor.description.

    This works for both ``sqlite3`` (which supports ``sqlite3.Row``) and the
    libSQL driver (which does not expose a row factory).
    """
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def init_db(db_path: str | None = None) -> None:
    """Create tables and indexes if they don't exist. Idempotent.

    Called once at backend startup. The parent directory is created if
    missing so the first boot on a fresh clone or container succeeds.

    If ``db_path`` is omitted, the configured connection factory is used
    (Turso in production, local SQLite in dev). If an explicit ``db_path`` is
    passed, a direct ``sqlite3`` connection is opened for testability.
    """
    if db_path is None:
        conn = _get_connection()
    else:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_student_created
        ON messages(student_id, created_at)
        """
    )
    conn.commit()


def get_or_create_student(display_name: str) -> int:
    """Return the id of the first student with this exact display_name.

    The match is case-sensitive ("Ana" != "ana"), which is SQLite's default
    behavior for ``=`` on ``TEXT``. If no row matches, a new student is
    inserted with ``created_at = utcnow()`` and the new id is returned.
    """
    conn = _get_connection()
    row = conn.execute(
        "SELECT id FROM students WHERE display_name = ?",
        (display_name,),
    ).fetchone()
    if row is not None:
        return row[0]

    cursor = conn.execute(
        "INSERT INTO students (display_name, created_at) VALUES (?, ?)",
        (display_name, _utc_now()),
    )
    conn.commit()
    return cursor.lastrowid


def get_student_by_name(display_name: str) -> int | None:
    """Return the `id` of the first row matching `display_name` (case-sensitive).

    Returns `None` if no student with that name exists. Does NOT create a row.
    """
    conn = _get_connection()
    row = conn.execute(
        "SELECT id FROM students WHERE display_name = ?",
        (display_name,),
    ).fetchone()
    return row[0] if row is not None else None


def get_message_owner(message_id: int) -> int | None:
    """Return the `student_id` of the message with `id = message_id`.

    Returns `None` if the message does not exist. Used to distinguish 404
    (no such message) from 403 (message exists but belongs to a different student).
    """
    conn = _get_connection()
    row = conn.execute(
        "SELECT student_id FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    return row[0] if row is not None else None


def save_message(student_id: int, role: str, content: str) -> int:
    """Insert a message row and return its id.

    ``role`` must be ``'user'`` or ``'assistant'``. Raises ``ValueError`` for
    any other value. ``created_at`` is set to the insertion time in UTC, not
    the request time.
    """
    if role not in _VALID_ROLES:
        raise ValueError(f"role must be one of {_VALID_ROLES}, got {role!r}")

    conn = _get_connection()
    cursor = conn.execute(
        """
        INSERT INTO messages (student_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (student_id, role, content, _utc_now()),
    )
    conn.commit()
    return cursor.lastrowid


def get_history(student_id: int, limit: int | None = None) -> list[dict]:
    """Return messages for a student, ordered by ``created_at ASC, id ASC``.

    Each element is a dict with keys ``id``, ``role``, ``content`` and
    ``created_at``. If ``limit`` is provided, only the last ``limit`` messages
    are returned, but they remain ordered chronologically (oldest of the slice
    first). An empty list is returned when the student has no messages.
    """
    conn = _get_connection()
    if limit is None:
        cursor = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE student_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (student_id,),
        )
    else:
        cursor = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM (
                SELECT id, role, content, created_at
                FROM messages
                WHERE student_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            )
            ORDER BY created_at ASC, id ASC
            """,
            (student_id, limit),
        )
    return _rows_to_dicts(cursor)


def delete_message(message_id: int, student_id: int) -> bool:
    """Delete the message with ``id = message_id`` AND ``student_id = student_id``.

    Returns ``True`` if a row was deleted, ``False`` if no matching row existed.
    This single-row delete intentionally does not cascade to paired messages;
    callers that want to remove a whole turn must call it twice.
    """
    conn = _get_connection()
    cursor = conn.execute(
        "DELETE FROM messages WHERE id = ? AND student_id = ?",
        (message_id, student_id),
    )
    conn.commit()
    return cursor.rowcount > 0

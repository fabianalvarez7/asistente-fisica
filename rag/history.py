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

import functools
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


class HistoryUnavailableError(Exception):
    """Raised after a persistence operation remains unavailable after retry."""


#: Cached connection, created lazily on first use and reused across requests.
_connection = None
_connection_lock = threading.Lock()

#: libsql_experimental is the Turso/libSQL driver used in production. It defines
#: its own exception class (``libsql_experimental.Error``) which inherits from
#: ``Exception`` -- NOT from the ``sqlite3`` hierarchy. We add it to the
#: ``_reconnect_on_failure`` catch-list so a stale Turso handle triggers a
#: reconnect instead of bubbling up as a 503.
#:
#: The import is wrapped in try/except so local dev (which uses plain
#: ``sqlite3`` and doesn't have the package installed) keeps working. When the
#: import fails, ``_LIBSQL_ERRORS`` is empty and the reconnect logic only
#: catches ``sqlite3`` errors.
try:
    import libsql_experimental as _libsql

    _LIBSQL_ERRORS = (_libsql.Error,)
except ImportError:  # pragma: no cover - dev environment without libsql
    _LIBSQL_ERRORS = ()

# Programming defects that should NEVER be silently degraded. They indicate
# real bugs (bad SQL, wrong argument type, missing attribute) that need to be
# fixed in code, not papered over by the chat falling back to history-less
# mode. Without this whitelist, ``_reconnect_on_failure`` would mask real
# defects as transient outages.
#
# ``sqlite3.ProgrammingError`` (bad SQL) and ``sqlite3.IntegrityError``
# (constraint violations) are explicitly excluded from degradation — a
# schema/code drift must surface so we fix it. ``sqlite3.OperationalError``
# is handled separately: its numeric result code distinguishes availability
# failures (BUSY, IOERR, CANTOPEN, ...) from SQL/schema defects (SQLITE_ERROR,
# SQLITE_SCHEMA, ...). The two are not interchangeable.
_PROGRAMMING_DEFECTS = (
    TypeError,
    ValueError,
    AttributeError,
    NameError,
    KeyError,
    IndexError,
    AssertionError,
    sqlite3.ProgrammingError,
    sqlite3.IntegrityError,
)

# SQLite reports both availability failures and SQL/schema defects as
# OperationalError. Classify by SQLite's numeric result code so malformed SQL
# and missing tables (SQLITE_ERROR) remain visible programming/schema failures.
# Extended result codes retain the primary code in their low byte.
_SQLITE_AVAILABILITY_CODES = frozenset(
    {
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
        sqlite3.SQLITE_READONLY,
        sqlite3.SQLITE_IOERR,
        sqlite3.SQLITE_FULL,
        sqlite3.SQLITE_CANTOPEN,
        sqlite3.SQLITE_PROTOCOL,
    }
)


def _is_history_availability_error(exc: Exception) -> bool:
    """Return whether a driver error represents persistence unavailability.

    Used only to classify ``sqlite3.OperationalError`` by result code inside
    ``_is_programming_defect``. The libsql and ``OSError`` branches remain
    here as documentation of what counts as availability across the stack,
    even though the catch-all decorator no longer relies on them.
    """
    if _LIBSQL_ERRORS and isinstance(exc, _LIBSQL_ERRORS):
        # libsql-experimental 0.0.55 exposes only one Error class, with no
        # stable subtype or machine-readable code. We deliberately prefer chat
        # availability after retry even though this can mask a driver-reported
        # schema/auth/config defect. Never parse Error.args or its text: they
        # may contain SQL, URLs, credentials, or other sensitive context.
        return True

    # libsql-experimental talks to Turso over sockets, so DNS failures,
    # connection refusals, TLS errors and read timeouts surface as raw
    # ``OSError`` (and its subclasses ``ConnectionError``, ``TimeoutError``,
    # ``socket.gaierror``) — NOT as ``libsql.Error``.
    if isinstance(exc, OSError):
        return True

    if not isinstance(exc, sqlite3.OperationalError):
        return False

    error_code = getattr(exc, "sqlite_errorcode", None)
    return (
        error_code is not None
        and error_code & 0xFF in _SQLITE_AVAILABILITY_CODES
    )


def _is_programming_defect(exc: Exception) -> bool:
    """Return whether an exception indicates a code defect that must propagate.

    Anything that is NOT a programming defect is treated as a transient
    availability failure: ``_reconnect_on_failure`` will reset the cached
    connection, retry once, and wrap as ``HistoryUnavailableError`` if the
    retry also fails.

    The whitelist is conservative on purpose. Adding more types here means
    more bugs surface as 500 instead of degraded chat; removing types here
    means more defects get silently masked. The trade-off we want is
    ``chat-stays-up-but-history-may-be-wrong`` for outages, and
    ``500-so-we-notice`` for code bugs.
    """
    if isinstance(exc, _PROGRAMMING_DEFECTS):
        return True
    # SQLite OperationalError is the one case where the same exception class
    # can mean either "DB unreachable" (BUSY, IOERR, CANTOPEN, ...) or
    # "bad SQL / schema drift" (SQLITE_ERROR, SQLITE_SCHEMA, ...). The
    # numeric result code distinguishes them — only the latter is a defect.
    if isinstance(exc, sqlite3.OperationalError):
        return not _is_history_availability_error(exc)
    return False


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
            _connection = _libsql.connect(url, auth_token=token)
        else:
            db_path = os.getenv(_SQLITE_PATH_ENV, _DEFAULT_DB_PATH)
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            # check_same_thread=False: FastAPI dispatches endpoints to a pool
            # of worker threads, and the cached connection is shared across
            # them. The module-level _connection_lock serializes access so we
            # don't need SQLite's per-thread guard. (Production uses Turso/
            # libSQL via the branch above — this only applies to local dev.)
            _connection = sqlite3.connect(db_path, check_same_thread=False)
            _connection.execute("PRAGMA journal_mode = WAL")
            _connection.execute("PRAGMA foreign_keys = ON")
        return _connection


def _reset_connection() -> None:
    """Drop the cached connection so the next call rebuilds it.

    Used as the recovery step when a connection-level error is caught by
    ``_reconnect_on_failure``: the next call to ``_get_connection`` will
    recreate the connection with the current env vars. Closing is
    best-effort — a broken handle may raise on ``close()`` and we don't
    care because we're discarding it anyway.
    """
    global _connection
    with _connection_lock:
        if _connection is not None:
            try:
                _connection.close()
            except Exception:
                # Closing a broken handle can raise; we are discarding it
                # anyway, so swallow and move on.
                pass
            _connection = None


def _reconnect_on_failure(func):
    """Decorator: classify the wrapped function's exceptions and degrade
    gracefully when they reflect persistence unavailability.

    Behavior:

    * Programming defects (bad SQL, wrong argument types, missing
      attributes, invariant violations, constraint failures) propagate
      as-is so they appear as 500 in the logs and get fixed in code.
      See ``_PROGRAMMING_DEFECTS`` and ``_is_programming_defect`` for
      the whitelist.
    * Anything else — ``libsql.Error``, ``OSError`` and its socket
      subclasses, ``sqlite3.OperationalError`` with BUSY/IOERR/CANTOPEN
      codes, and any future exception type we have not seen — is treated
      as availability. The cached connection is discarded, the wrapped
      function is called once more (which rebuilds a fresh connection
      via ``_get_connection``), and if that retry also fails for any
      non-defect reason the error is wrapped as ``HistoryUnavailableError``
      so the chat endpoints can keep the UX alive without history.

    This is a catch-all by design. ``libsql-experimental`` is in 0.0.55
    and the next layer in the stack may surface a new exception class at
    any time. Earlier versions of this decorator caught only a narrow set
    (``sqlite3.OperationalError``, then ``libsql.Error``, then
    ``OSError``), and each gap was discovered only after a Turso outage
    took the chat down in production. See ``docs/gotchas.md`` for the
    timeline. The catch-all eliminates the whack-a-mole: any new
    exception type that is not a recognized programming defect now
    degrades gracefully out of the box.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            # ``BaseException`` subclasses (KeyboardInterrupt, SystemExit,
            # asyncio.CancelledError, GeneratorExit) are NOT caught by
            # ``except Exception`` and propagate unchanged — that is the
            # intended behavior.
            if _is_programming_defect(exc):
                raise
            _reset_connection()
            try:
                return func(*args, **kwargs)
            except Exception as retry_exc:
                if _is_programming_defect(retry_exc):
                    raise
                raise HistoryUnavailableError(
                    "History persistence remained unavailable after reconnect"
                ) from retry_exc
    return wrapper


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


@_reconnect_on_failure
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
        conn = sqlite3.connect(db_path, check_same_thread=False)
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


@_reconnect_on_failure
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


@_reconnect_on_failure
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


@_reconnect_on_failure
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


@_reconnect_on_failure
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


@_reconnect_on_failure
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


@_reconnect_on_failure
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

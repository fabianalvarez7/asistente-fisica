# Design: Persistent History (Turso Migration)

> **Change**: `2026-08-14-persistent-history`
> **Predecessor**: `2026-07-22-student-history`

## Technical Approach

Replace the local SQLite file at `data/historial.db` with a Turso (libSQL) remote database, while keeping every other layer of the persistence contract identical. The schema, DDL, queries, public function signatures, and downstream consumers (`app/main.py`, `rag/chain.py`) are untouched. The migration is a connection-layer swap in `rag/history.py`, plus env-var wiring and an AGENTS.md update. See `proposal.md` for intent and `specs/conversation-persistence/spec.md` for the contract.

## Architecture Decisions

### Decision: Connection layer — singleton with lazy init + lock

**Choice**: Module-level `_connection` cache, lazily initialized inside a `threading.Lock`. The factory `_get_connection()` returns the cached connection; first call decides Turso vs local SQLite from env vars and stashes the result globally. Every public function (`init_db`, `get_or_create_student`, `save_message`, `get_history`, `delete_message`, etc.) opens the cached connection with `with conn:` instead of `with sqlite3.connect(...) as conn:`.

**Alternatives considered**: per-request connection (slower, contradicts the explore's "reuse across requests" requirement); connection pool (overkill for a single-process FastAPI app at this scale).

**Rationale**: FastAPI runs in a single process; one connection per process is sufficient for the prototype (~50–100 students, ~1k messages/semester). Lazy init keeps boot-time tolerant of a temporarily-unreachable Turso. The lock makes first-call thread-safe under FastAPI's async workers. Existing pragmas (`journal_mode = WAL`, `foreign_keys = ON`) only run on the local-SQLite branch — libSQL applies them internally.

### Decision: libSQL Python driver

**Choice**: `libsql-experimental>=0.1,<1.0` (Turso's official Python driver). Verify the current PyPI version at apply time and tighten the pin if a stable release exists.

**Alternatives considered**: `libsql-client` (older, less maintained); raw HTTP via `requests` (works but adds manual SQL plumbing and loses cursor semantics); SQLAlchemy + libsql dialect (overkill).

**Rationale**: Official driver maintained by Turso Labs; SQLite-compatible API; supports both local files and remote URLs. The `experimental` tag is the project's current convention; the spec and proposal already committed to it.

### Decision: Mid-request DB error handling

**Choice**: Wrap each `rag/history.py` call site in `app/main.py` with `try/except`. Catch `(sqlite3.Error, Exception)` from libSQL. On error during a `POST /chat` flow: emit an SSE error frame (`event: error\ndata: {...}\n\n`), then `data: [DONE]\n\n`, and terminate. Do NOT persist a fabricated assistant message. The user message MAY be persisted before the failure (matches the existing pattern in `app/main.py:142–148`); if the failure happens before persistence, the message is lost.

**Alternatives considered**: HTTP 503 (cleaner status, but breaks SSE mid-stream); silent retry with backoff (hides the problem, adds latency).

**Rationale**: SSE streams cannot change status code after the first byte. An error frame is the SSE convention for in-flight failures. Mirroring the existing Groq error-handling pattern keeps the consumer (`chat.js`) code-shape consistent.

### Decision: Schema bootstrap on Turso

**Choice**: Rely on `CREATE TABLE IF NOT EXISTS` idempotency in `init_db()`. The first request after deploy triggers the factory, the connection is opened, the schema is created. No separate migration script.

**Alternatives considered**: explicit migration tool (overkill for SQLite); manual `turso db shell` bootstrap (fragile, manual step).

**Rationale**: The DDL is portable SQLite. `init_db()` is already idempotent. The Turso DB starts empty — no data migration from `data/historial.db` (per operational decision).

## Data Flow

```
Browser (chat.js)
    │
    │  POST /chat  { query, student_name }
    ▼
FastAPI handler (app/main.py)
    │
    │  get_or_create_student(student_name)  ──┐
    │  save_message(..., 'user', query)      │  try/except
    │  generate_response(query, history)     │  wraps each
    │  save_message(..., 'assistant', resp)  ─┘
    │
    ▼
rag/history.py  ── _get_connection() ──┐
                                          │
        if TURSO_DATABASE_URL and         │
           TURSO_AUTH_TOKEN:              │
                ▼                          │
        libsql_experimental                │
                .connect(url,              │
                         auth_token=token) │
        else:                              │
                ▼                          │
        sqlite3.connect(SQLITE_PATH)       │
                + PRAGMAs                  │
                                          │
                                          ▼
                              [Turso remote DB]
                              [or local SQLite file]
```

Error paths: connection factory init fails → 503 SSE error frame; mid-request `save_message` fails → same; Groq stream fails → same as today.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `rag/history.py` | Modify | Replace `_db_path()` with `_get_connection()` factory + module-level cache. Update every `with sqlite3.connect(_db_path()) as conn` to `with _get_connection() as conn`. Keep `_configure_connection()` as a no-op shim (libSQL doesn't need it but keeping the helper means the diff stays small). |
| `.env.example` | Modify | Add `TURSO_DATABASE_URL=` and `TURSO_AUTH_TOKEN=` (empty placeholders + comment pointing to Turso dashboard). Keep `SQLITE_PATH` with a "dev-only fallback" note. |
| `requirements.txt` | Modify | Add `libsql-experimental>=0.1,<1.0`. |
| `openspec/specs/conversation-persistence/spec.md` | Modify | Apply the delta from `specs/conversation-persistence/spec.md` in this change folder. |
| `AGENTS.md` | Modify | Rewrite §7 decision #12: drop "ephemeral disk" trade-off paragraph; document Turso migration and HF Secrets requirement. |

## Interfaces / Contracts

```python
# rag/history.py — new factory (replaces _db_path)
import os, sqlite3, threading

_SQLITE_PATH_ENV = "SQLITE_PATH"
_DEFAULT_DB_PATH = "./data/historial.db"
_TURSO_URL_ENV = "TURSO_DATABASE_URL"
_TURSO_TOKEN_ENV = "TURSO_AUTH_TOKEN"

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


def _configure_connection(conn):  # kept as a no-op for diff minimality
    pass  # libSQL handles pragmas internally; sqlite3 branch already configured above.
```

Public function signatures stay identical. The only call-site change is `sqlite3.connect(_db_path())` → `_get_connection()`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|---------|
| Unit | `_get_connection()` returns libSQL client when env vars set, local SQLite otherwise; cached across calls | pytest with monkeypatched env vars and a mocked `libsql.connect` |
| Integration | End-to-end chat → row exists in Turso | Hit `POST /chat` from a local backend with real Turso creds; query `turso db shell` to confirm the row |
| Regression | Existing smoke queries still pass | Re-run `tests/socratic_layer_run_2026-08-07.md` |
| Manual | History survives HF Space cold start | Send a chat, force a container restart (`Settings → Restart Space`), hit `GET /history`, confirm the message is still there |

## Migration / Rollout

No data migration. Turso starts empty. Old `data/historial.db` (dev/test data) is abandoned. Rollout:
1. Add HF Space Secrets `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`.
2. Deploy the new code (factory + libsql dep).
3. Verify: send one chat message, confirm it lands in Turso via dashboard.
4. Verify: cold-restart the Space, send another message, confirm the first one is in `GET /history`.

Rollback: `git revert` the change commit. The factory degrades to local SQLite (silent fallback), but in practice rolling back also means removing HF Secrets or restoring the SQLite path env var.

## Open Questions

- [ ] Exact libsql-experimental version to pin — verify on PyPI at apply time.
- [ ] Confirm `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are accepted as HF Space Secret names (HF allows alphanumeric + underscores; should be fine).
- [ ] Optional follow-up (out of scope here): a startup-time WARNING log when production deploy falls back to local SQLite, to catch misconfiguration.
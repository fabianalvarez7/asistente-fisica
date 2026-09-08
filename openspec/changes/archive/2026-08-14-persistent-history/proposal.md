# Proposal: Persistent History (Turso Migration)

> **Status**: draft
> **Change**: `2026-08-14-persistent-history`
> **Predecessor**: `2026-07-22-student-history` (archived)

## Intent

The conversation history persistence layer is fully implemented — typed-name identification, SQLite schema, message lifecycle, history injection into Groq, and delete endpoints are all shipped and documented in `openspec/specs/conversation-persistence/spec.md`. The only gap is that SQLite lives on HF Spaces' ephemeral disk; history is lost when the Space sleeps (~48h inactivity). AGENTS.md §7 decisions #11 and #12 explicitly accept this trade-off for the prototype, but the team now wants to fix it.

This change migrates the conversation database from a local SQLite file to Turso (libSQL, SQLite-compatible, free tier 9 GB). The schema, queries, and API remain identical — the migration is a connection-string change, not a rewrite. The frontend fix (localStorage for the student's display name) is already shipped (`app/static/chat.js:28,230`) and requires no additional work.

## Scope

### In Scope
- **Turso connection in `rag/history.py`**: replace `_db_path()` + `sqlite3.connect()` with a connection factory that returns a libSQL client when `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are set, falling back to local SQLite only when both are unset (dev convenience).
- **Environment variables**: add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` to `.env.example` with comments explaining where to get them (Turso dashboard → database → CLI).
- **Dependency**: add `libsql-experimental` to `requirements.txt`.
- **Spec update**: delta update to `openspec/specs/conversation-persistence/spec.md` — replace the "Database file location and writability" requirement with Turso connection requirements.
- **AGENTS.md update**: rewrite §7 decision #12 to document the Turso migration. Remove the "ephemeral disk" trade-off line.

### Out of Scope
- Replacing typed-name identification with cursada conditions or any other identity scheme (separate future change).
- Real authentication (passwords, sessions, tokens).
- Local SQLite fallback in production (Turso for both dev and deploy).
- Migrating existing `data/historial.db` test data to Turso (start empty).
- Pagination of long history (future change).
- Multi-device sync (already inherent in Turso — no explicit work needed).
- Dockerfile changes (Turso is a remote connection; the container code is unchanged).
- Frontend changes (localStorage for name is already shipped).

## Capabilities

> This section is the CONTRACT between proposal and specs phases.
> The sdd-spec agent reads this to know exactly which spec files to create or update.

### New Capabilities
None.

### Modified Capabilities
- `conversation-persistence`: The "Database file location and writability" requirement changes from local SQLite file to remote Turso database. The schema, queries, persistence lifecycle, history injection, and deletion endpoints are unchanged. The "Directory is auto-created" scenario is removed (no local directory needed). A new scenario "Turso connection is established on first request" is added. The `SQLITE_PATH` env var is deprecated in favor of `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN`.

## Approach

### Connection Factory

`rag/history.py` replaces `_db_path()` with a `_get_connection()` factory:

```python
def _get_connection():
    """Return a libSQL connection if Turso env vars are set, else local SQLite."""
    url = os.getenv("TURSO_DATABASE_URL")
    token = os.getenv("TURSO_AUTH_TOKEN")
    if url and token:
        import libsql_experimental as libsql
        return libsql.connect(url, auth_token=token)
    else:
        db_path = os.getenv("SQLITE_PATH", _DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return sqlite3.connect(db_path)
```

Every public function (`init_db`, `get_or_create_student`, `save_message`, `get_history`, `delete_message`, `get_student_by_name`, `get_message_owner`) replaces `sqlite3.connect(_db_path())` with `_get_connection()`. The `_configure_connection()` helper (WAL mode + foreign keys) remains for local SQLite but is a no-op for Turso (libSQL handles these internally).

### Schema

No changes. The existing `students` and `messages` tables are created via `CREATE TABLE IF NOT EXISTS` on first connection. Turso is SQLite-compatible, so the DDL is identical. The Turso database starts empty — no migration of `data/historial.db` test data.

### Environment Variables

`.env.example` gains two new entries:

```bash
# Turso database for conversation history (persistent across HF Spaces sleep).
# Get these from the Turso dashboard: https://app.turso.tech → your database → CLI.
# If both are unset, the backend falls back to local SQLite (dev convenience only).
TURSO_DATABASE_URL=
TURSO_AUTH_TOKEN=
```

`SQLITE_PATH` remains in `.env.example` but is documented as a dev-only fallback. In production (HF Spaces), both Turso vars MUST be set.

### Dependency

`requirements.txt` gains `libsql-experimental` (Turso's Python driver). No other dependencies change.

### What Does NOT Change

- `app/main.py`: the API endpoints (`POST /chat`, `GET /history`, `DELETE /messages/{id}`) are unchanged. They call `rag/history.py` functions, which now connect to Turso instead of a local file.
- `app/static/chat.js`, `app/static/index.html`, `app/static/style.css`: no frontend changes.
- `rag/chain.py`: history injection into Groq is unchanged.
- `Dockerfile`: no changes. The `/app/data` directory is no longer used for history but may still be used for other ephemeral data.
- `rag/retrievers/*`, `rag/loaders/*`, `rag/splitters/*`, `rag/prompts/*`, `dashboard/*`: untouched.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `rag/history.py` | Modified | Replace `_db_path()` + `sqlite3.connect()` with `_get_connection()` factory. All public functions updated. `_configure_connection()` becomes conditional (local SQLite only). |
| `.env.example` | Modified | Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`. Deprecate `SQLITE_PATH` (dev-only fallback). |
| `requirements.txt` | Modified | Add `libsql-experimental`. |
| `openspec/specs/conversation-persistence/spec.md` | Modified | Delta update: replace "Database file location and writability" requirement with Turso connection requirements. Remove "Directory is auto-created" scenario. Add "Turso connection is established on first request" scenario. |
| `AGENTS.md` | Modified | Rewrite §7 decision #12 to document the Turso migration. Remove the "ephemeral disk" trade-off. |

**NOT affected**: `app/main.py`, `app/static/*`, `rag/chain.py`, `rag/retrievers/*`, `rag/loaders/*`, `rag/splitters/*`, `rag/prompts/*`, `dashboard/*`, `Dockerfile`, `scripts/*`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Turso credentials leaked in git** | Low | `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are added to `.env.example` as empty placeholders. `.env` is gitignored. HF Spaces uses Secrets (not `.env`). Code review checks for hardcoded values. |
| **`libsql-experimental` package is unstable or abandoned** | Low | The package is maintained by Turso Labs. If it breaks, the fallback is to use `sqlite3` with Turso's HTTP API (more work, but viable). Pin the version in `requirements.txt`. |
| **Turso network latency slows down the chat** | Low | At the prototype's scale (~50-100 students, ~1000 messages/semester), latency is ~10-50 ms per query — negligible. If latency becomes a problem, cache history in memory (but this defeats the purpose of Turso). |
| **Turso free tier limits exceeded** | Low | Free tier: 9 GB storage, 100 GB transfer/month. Prototype uses ~50 MB storage and ~10 GB transfer. Monitor via Turso dashboard. Upgrade to paid tier ($29/month) if needed. |
| **Turso service disruption** | Low | Handle connection errors gracefully. Return 503 with a user-friendly message. The existing error-handling pattern in `app/main.py:142-148` already catches exceptions. |
| **Local dev without Turso vars breaks** | Low | The connection factory falls back to local SQLite when both Turso vars are unset. Local dev works without a Turso account. |
| **Schema mismatch between local SQLite and Turso** | Low | Both use the same DDL (`CREATE TABLE IF NOT EXISTS`). Test on a fresh Turso database before deploying. If schema drift occurs, run `init_db()` on Turso to create the tables. |
| **Breaking the existing demo** | Low | The migration is a connection-string change, not a rewrite. All existing endpoints and queries work unchanged. Test the smoke queries from `tests/socratic_layer_run_2026-08-07.md` to ensure no regression. |

## Rollback Plan

`git revert` of the commit(s) touching `rag/history.py`, `.env.example`, `requirements.txt`, `openspec/specs/conversation-persistence/spec.md`, and `AGENTS.md`. The backend falls back to local SQLite (the connection factory detects missing Turso vars and uses `sqlite3.connect()`). The Turso database is not deleted — it can be re-connected later if needed. No model swap, no embedding re-bake, no deployment config change. Rollback is a single revert.

## Dependencies

- Turso account created (Fabián confirmed). Database URL and auth token available from the Turso dashboard.
- Socratic layer and student-history changes must be deployed (predecessors).
- `libsql-experimental` Python package available on PyPI (confirmed).

## Success Criteria

- [ ] `GET /history?student_name=X` returns history across an HF Space cold start (sleep → wake → history still present).
- [ ] `POST /chat` persists messages to Turso (verifiable via Turso CLI or dashboard).
- [ ] Existing tests (if any) still pass.
- [ ] Smoke test queries from `tests/socratic_layer_run_2026-08-07.md` still pass with no regression.
- [ ] Local dev works without Turso vars (falls back to local SQLite).
- [ ] HF Spaces deploy works with Turso vars set as Secrets.
- [ ] AGENTS.md §7 decision #12 documents the Turso migration.
- [ ] `openspec/specs/conversation-persistence/spec.md` reflects the Turso connection requirements.

## Out of Scope but Flagged for Follow-Up

- **Typed-name replacement with cursada conditions**: a future change will replace the typed-name identification with a more robust identity scheme tied to the course roster (cursada conditions). This is a separate change, not part of this migration.
- **Pagination of long history**: the frontend currently renders all messages. If a student accumulates 500+ messages over a semester, pagination will be needed. Separate change.
- **Real authentication (passwords, sessions, tokens)**: the prototype uses typed-name identification (spoofable, no privacy). If the prototype graduates to production, real auth will be needed. Separate change.
- **Multi-conversation model**: the prototype uses one continuous thread per student. If students need to organize by exercise/topic, a multi-conversation model will be added. Separate change.

## References

- `openspec/changes/2026-08-14-persistent-history/explore.md` — full exploration (384 lines).
- `openspec/changes/archive/2026-07-22-student-history/proposal.md` — predecessor proposal (structural reference).
- `openspec/specs/conversation-persistence/spec.md` — spec to be updated (delta, not rewrite).
- `AGENTS.md` §7 decisions #11 (typed-name identification) and #12 (HF Spaces ephemeral disk trade-off).
- `rag/history.py` — current implementation (230 lines, standalone SQLite module).

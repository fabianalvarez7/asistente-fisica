# Tasks: Persistent History (Turso Migration)

> **Status**: ready for apply
> **Change**: `2026-08-14-persistent-history`
> **Predecessor**: `2026-07-22-student-history` (archived)

Migrate conversation history from local SQLite on HF Spaces' ephemeral disk to Turso (libSQL remote DB). Connection-layer swap in `rag/history.py`; schema, queries, and API unchanged.

**Total tasks**: 7 | **Estimated commits**: 6 (Task 7 is a deploy action)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150 (well under the 400-line review budget) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All 6 code+docs commits in one PR | Single PR to main | ~150 lines; tightly coupled; single PR is appropriate |

---

## Dependency Graph

```
1 ──→ 2 ──→ 3 ──→ 4
               ├─→ 5
               └─→ 6
                       └─→ 7 (deploy, after all commits)
```

- Tasks 1 → 2 → 3 → 4: sequential (each depends on the previous).
- Tasks 5 and 6: can run in parallel after Task 3.
- Task 7: runs after all code+docs commits are merged.

---

## Phase 1: Foundation

### 1. Add libsql-experimental to requirements.txt

**Files**: `requirements.txt`
**Depends on**: none
**Commit**: `chore(deps): add libsql-experimental for Turso support`

- [x] Add `libsql-experimental>=0.0.55,<1.0` under a new `# History persistence` section (pin range tightened at apply time — no `0.1+` release exists on PyPI yet).
- [x] Verify current PyPI version before committing; tighten pin if a stable release exists.

**Acceptance**: `pip install -r requirements.txt` succeeds; `python -c "import libsql_experimental"` runs without error.
**Verification**: `pip install -r requirements.txt && python -c "import libsql_experimental; print(libsql_experimental.__name__)"`

---

### 2. Add Turso env vars to .env.example

**Files**: `.env.example`
**Depends on**: Task 1
**Commit**: `chore(env): add TURSO_* vars and mark SQLITE_PATH as dev-only`

- [x] Add `TURSO_DATABASE_URL=` and `TURSO_AUTH_TOKEN=` with empty values.
- [x] Add comments explaining where to get credentials (Turso dashboard → database → CLI).
- [x] Update `SQLITE_PATH` comment to note it is a dev-only fallback when Turso vars are unset.

**Acceptance**: `.env.example` contains both `TURSO_*` vars with empty values and explanatory comments; `SQLITE_PATH` is annotated as dev-only.
**Verification**: `grep -c TURSO .env.example` returns `2` or more.

---

## Phase 2: Core Implementation

### 3. Refactor rag/history.py with connection factory

**Files**: `rag/history.py`
**Depends on**: Task 1, Task 2
**Commit**: `refactor(history): swap SQLite factory for Turso-or-local connection layer`

- [x] Add `import threading` and module-level `_connection = None` + `_connection_lock = threading.Lock()`.
- [x] Add Turso env constants `_TURSO_URL_ENV` and `_TURSO_TOKEN_ENV`.
- [x] Replace `_db_path()` with `_get_connection()`: returns cached libSQL client when both Turso vars set, else local SQLite with WAL + FK pragmas.
- [x] Update every public function: replace `with sqlite3.connect(_db_path()) as conn` + `_configure_connection(conn)` with `conn = _get_connection()` (use `with conn:` for transaction blocks).
- [x] Keep `_configure_connection()` as a no-op shim for diff minimality.
- [x] `init_db()` uses `_get_connection()` instead of `sqlite3.connect(db_path)` when `db_path` is None; when an explicit `db_path` is passed, keep the direct `sqlite3.connect(db_path)` path for testability.

**Acceptance**: code compiles; `_get_connection()` returns a libSQL client when `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` are set; returns local SQLite connection otherwise; connection is cached across calls.
**Verification**:
```bash
# Local fallback (no Turso vars):
python -c "from rag.history import _get_connection; c = _get_connection(); print(type(c))"
# Should print <class 'sqlite3.Connection'>

# With Turso vars (use test creds):
TURSO_DATABASE_URL=libsql://test-db-org.turso.io TURSO_AUTH_TOKEN=fake python -c "from rag.history import _get_connection; c = _get_connection(); print(type(c).__module__)"
# Should print libsql_experimental (or fail with auth error — confirms driver is reached)
```

---

### 4. Wrap DB calls in app/main.py with error handling

**Files**: `app/main.py`
**Depends on**: Task 3
**Commit**: `fix(chat): handle DB errors mid-request with SSE error frame`

- [x] Wrap `get_or_create_student`, `save_message(user)`, `get_history` calls in `POST /chat` with `try/except (Exception)`. On DB error before Groq: raise `HTTPException(503)` with a Spanish message.
- [x] Inside `event_generator`, wrap `save_message(assistant, ...)` calls with `try/except`. On failure: emit SSE `event: error` frame + `data: [DONE]`, do NOT persist a fabricated message.
- [x] Wrap `GET /history` and `DELETE /messages/{id}` endpoint DB calls with `try/except`. On error: raise `HTTPException(503)`.

**Acceptance**: code compiles; setting `TURSO_AUTH_TOKEN` to an invalid value and sending a chat produces an SSE error frame (not a crash or fabricated message); `GET /history` returns 503 on DB failure.
**Verification**:
```bash
# Start with invalid Turso token:
TURSO_DATABASE_URL=libsql://test.turso.io TURSO_AUTH_TOKEN=invalid uvicorn app.main:app --reload
# POST /chat should return SSE error frame, not a 500 or fabricated response.
```

---

## Phase 3: Documentation

### 5. Apply spec delta to conversation-persistence

**Files**: `openspec/specs/conversation-persistence/spec.md`
**Depends on**: Task 3
**Commit**: `docs(spec): apply persistent-history delta to conversation-persistence`

- [x] Replace "Database file location and writability" requirement with Turso connection requirements from the delta spec.
- [x] Add scenarios: "Turso connection is established on first request", "Local SQLite fallback when Turso vars are unset", "Turso connection failure returns 503", "Turso service disruption mid-request".
- [x] Add requirement: "Turso credentials required in production deployment" with HF Spaces Secrets scenarios.
- [x] Remove scenario: "Directory is auto-created" (no longer relevant for Turso; local fallback still auto-creates but is dev-only).

**Acceptance**: spec file reflects Turso as the production DB; all delta scenarios are present; "Directory is auto-created" scenario is removed.
**Verification**: `grep -c "Turso" openspec/specs/conversation-persistence/spec.md` returns 3+.

---

### 6. Update AGENTS.md §7 decision #12

**Files**: `AGENTS.md`
**Depends on**: Task 3
**Commit**: `docs(agents): update §7 #12 — history persistence via Turso`

- [x] Rewrite decision #12 to document the Turso migration.
- [x] Remove the "ephemeral disk" trade-off paragraph.
- [x] Add note that HF Spaces must have `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` configured as Secrets.
- [x] Update §12 Environment Variables table: add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` rows.

**Acceptance**: §7 #12 reflects Turso architecture; no mention of "ephemeral disk" trade-off; §12 table includes Turso vars.
**Verification**: `grep "ephemeral" AGENTS.md` returns 0 matches in §7 #12 context.

---

## Phase 4: Deploy & Verify

### 7. Deploy and verify on HF Spaces

**Files**: none (deploy action)
**Depends on**: Tasks 1–6 (all commits merged)
**Commit**: NO commit (deploy action, not code)

- [ ] Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as HF Space Secrets.
- [ ] Push the change to the HF Space repo per `docs/hf-space.md` deploy flow.
- [ ] Send a chat message; confirm the row exists in Turso (via dashboard or `turso db shell`).
- [ ] Cold-restart the Space (Settings → Restart); send another message; confirm the first message is in `GET /history`.

**Acceptance**: history survives an HF Space cold start — `GET /history?student_name=X` returns messages sent before the restart.
**Verification**:
```bash
# After restart:
curl https://<space-url>/history?student_name=TestStudent
# Response should include messages sent before the restart.
```

---

## Line Count Estimates

| File | Type | Est. Changed Lines |
|------|------|-------------------|
| `requirements.txt` | modify | ~2 |
| `.env.example` | modify | ~8 |
| `rag/history.py` | modify | ~40 |
| `app/main.py` | modify | ~45 |
| `openspec/specs/conversation-persistence/spec.md` | modify | ~30 |
| `AGENTS.md` | modify | ~15 |
| **Total** | | **~140** |

# Apply Progress: Student History & Basic Identification

## Status

**partial**

Tasks 1 and 2 are complete and verified. Tasks 3-6 remain pending and will be
implemented in subsequent sessions as instructed.

## Branch

`feat/student-history`

## Commits

| SHA | Message |
|-----|---------|
| `42d61a4` | `feat(rag): add SQLite history module with student + message tables` |
| `58fe5aa` | `feat(rag): inject conversation history into Groq messages list` |

## Diff Summary

| File | Action | Δ lines |
|------|--------|---------|
| `rag/history.py` | Created | +194 / -0 |
| `rag/chain.py` | Modified | +25 / -6 |
| `openspec/changes/student-history/tasks.md` | Modified | +215 / -0 |
| `openspec/changes/student-history/apply-progress.md` | Modified | +185 / -0 |
| **Total (review budget)** | | **+425 / -6** |

## Tasks Completed

- [x] **1** — Added `rag/history.py` with `sqlite3` stdlib. Implements
  `init_db`, `get_or_create_student`, `save_message`, `get_history`, and
  `delete_message` exactly as specified in `design.md`. Schema includes
  `students`, `messages`, and `idx_messages_student_created`. Timestamps are
  ISO 8601 UTC strings. Foreign keys and WAL mode are enabled per connection.
- [x] **2** — Added `history: list[dict] | None = None` parameter to
  `generate_response` in `rag/chain.py`. When truthy, history is injected
  between `_FEW_SHOT` and the current query, producing
  `[system, ...few-shot..., ...history..., user-query]`. When `None` or `[]`,
  the assembled messages list is byte-for-byte identical in shape to the prior
  single-turn form. Added a dev-mode gate: when `PRODUCTION` is unset, the
  assembled list is printed to stdout as `[MSG NN] {role} | {preview}...`.
  `_FEW_SHOT` content/order and the system prompt are unchanged. No SQLite or
  I/O side effects were introduced; `generate_response` remains a pure
  generator.
- [ ] **3** — Deferred.
- [ ] **4** — Deferred.
- [ ] **5** — Deferred.
- [ ] **6** — Deferred.

## Test Results

### Task 1

- **File**: manual smoke test via Python script (`/tmp/test_history_smoke.py`)
- **Tests run**: 15 / 15
- **Pass / fail**: 15 / 0
- **Blocker**: none

```text
PASS: init_db('/tmp/test_history.db') succeeds
PASS: get_or_create_student('Ana') returns 1
PASS: get_or_create_student('Beto') returns 2
PASS: get_or_create_student('Ana') again returns 1
PASS: save_message(1, 'user', 'hola') returns 1
PASS: save_message(1, 'assistant', ...) returns 2
PASS: save_message(2, 'user', 'test') returns 3
PASS: get_history(1) returns 2 messages ordered ASC
PASS: get_history(1, limit=1) returns only the last message
PASS: delete_message(1, 1) returns True
PASS: delete_message(1, 1) again returns False
PASS: delete_message(3, 1) returns False
PASS: get_or_create_student('ana') returns new id 3 (case-sensitive)
PASS: schema contains students, messages, and index
PASS: save_message(1, 'system', ...) raises ValueError

All 15 checks passed.
```

### Task 2

- **File**: manual smoke test via Python script (`/tmp/test_chain_history_smoke.py`)
- **Tests run**: 10 / 10
- **Pass / fail**: 10 / 0
- **Blocker**: none

```text
PASS: history parameter present
PASS: history default is None
PASS: _FEW_SHOT has 6 entries
PASS: SYSTEM_PROMPT is str
PASS: no-history shape matches single-turn
PASS: history-injected shape is correct
PASS: empty history matches no-history shape
PASS: dev-mode gate prints indexed messages
PASS: PRODUCTION suppresses dev dump
PASS: chain.py does not import sqlite3

10/10 checks passed.
```

## SHALL Coverage (conversation-persistence spec)

| SHALL | Requirement | Covered by |
|-------|-------------|------------|
| SQLite schema for students and messages | Task 1 (`init_db`) |
| First startup creates tables | Task 1 (`init_db` idempotent `CREATE TABLE IF NOT EXISTS`) |
| Subsequent startup is idempotent | Task 1 (`CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`) |
| History retrieval shape | Task 1 (`get_history` returns `id`, `role`, `content`, `created_at`) |
| Single-message delete scoped to owner | Task 1 (`delete_message` requires matching `message_id` + `student_id`) |
| Database file location configurable | Task 1 (private `_db_path()` reads `SQLITE_PATH`) |
| Directory auto-created | Task 1 (`init_db` calls `os.makedirs`) |
| History injection into Groq `messages` list | Task 2 (`generate_response` builds `[system, few-shot, history, query]`) |
| Default window of 10 is injected | Task 3 (caller passes `get_history(student_id, limit=HISTORY_WINDOW)`) |
| Window configurable via env var | Task 3 (caller reads `HISTORY_WINDOW` env var) |
| Empty history yields no injection | Task 2 (`if history:` guard) |
| Order/content of system/few-shot preserved | Task 2 (literal `_FEW_SHOT` and `SYSTEM_PROMPT` unchanged) |
| Token budget for injected history | Design analysis (N=10 × 2 × ~150 tokens ≈ 3000 tokens) |

The persistence lifecycle, endpoints, frontend, and manual test plan will be
covered by Tasks 3-6.

## Deviations from Design

1. **No `get_connection()` helper** (Task 1): the orchestrator's task instructions
   required each public function to open its own connection, so the module uses
   a private `_db_path()` helper that reads `SQLITE_PATH` and returns a path
   string. Each function then calls `sqlite3.connect()` independently. WAL mode
   and `PRAGMA foreign_keys = ON` are still enabled per connection via a shared
   `_configure_connection(conn)` helper. This preserves the "no module-level
   connection" rule while keeping the implementation DRY.
2. **`ON DELETE CASCADE` on `messages.student_id`** (Task 1): the concrete requirements
   explicitly required this clause, so it is present even though the design.md
   SQL snippet did not show it. Behavior is unchanged for the prototype because
   the module does not expose a student-delete operation.
3. **No `context_chunks` parameter in `generate_response`** (Task 2): the design.md
   sketch included `context_chunks: list[str]` in the signature, but the current
   chain still performs retrieval internally and Task 2's acceptance criteria
   only required adding `history`. Adding `context_chunks` would have required
   moving retrieval out of `chain.py`, which is out of scope for Task 2. Task 3
   is expected to call `generate_response(query, history=history)`; the caller
   handles persistence and history retrieval, while `chain.py` retains its
   existing retrieval responsibility.

## Blockers

None for Tasks 1-2. The next batch (Task 3) depends on Tasks 1 and 2, which are
now complete.

## Rollback Confirmation

Rolling back Tasks 1-2 requires reverting the two commits and deleting the DB
file if it has been initialized:

```bash
git revert 58fe5aa
git revert 42d61a4
rm -f data/historial.db
```

No other modules have been modified, so no further rollback is needed.

## Out-of-Scope Check

Changes so far are limited to:

- `rag/history.py` (Task 1)
- `rag/chain.py` (Task 2)
- `openspec/changes/student-history/tasks.md`
- `openspec/changes/student-history/apply-progress.md`

No changes were made to:

- `app/main.py` or `app/static/`
- `dashboard/`
- `requirements.txt`
- `.env.example` or `AGENTS.md`

## Next Recommended

Task 3 in the next session: add FastAPI endpoints and persistence lifecycle to
`app/main.py` (`ChatRequest.student_name`, `POST /chat` persistence wrapper,
`GET /history`, `DELETE /messages/{id}`, and boot-time `init_db()`).

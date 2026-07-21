# Apply Progress: Student History & Basic Identification

## Status

**partial**

Tasks 1-4 are complete and verified. Tasks 5-6 remain pending and will be
implemented in subsequent sessions as instructed.

## Branch

`feat/student-history`

## Commits

| SHA | Message |
|-----|---------|
| `42d61a4` | `feat(rag): add SQLite history module with student + message tables` |
| `58fe5aa` | `feat(rag): inject conversation history into Groq messages list` |
| `9cb7d6a` | `feat(app): add student history endpoints and persistence lifecycle` |
| `ec021b0` | `feat(rag): add get_student_by_name and get_message_owner public read helpers` |
| `48eac7e` | `refactor(app): use public read helpers from rag/history.py` |
| `09bb749` | `docs(apply): record Task 3 deviation fix and helper smoke test results` |
| `d3513f0` | `feat(app): expose message IDs in SSE stream` |
| `c56d840` | `feat(ui): add student name gate, history rendering, and message delete` |

## Diff Summary

| File | Action | Δ lines |
|------|--------|---------|
| `rag/history.py` | Created | +194 / -0 |
| `rag/chain.py` | Modified | +25 / -6 |
| `app/main.py` | Modified | +124 / -7 |
| `openspec/changes/student-history/tasks.md` | Modified | +8 / -8 |
| `openspec/changes/student-history/apply-progress.md` | Modified | +185 / -0 |
| **Total (review budget)** | | **+546 / -21** |

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
- [x] **3** — Modified `app/main.py` to add `student_name` to `ChatRequest`,
  wrapped `POST /chat` with the persistence lifecycle (get/create student → save
  user message → fetch history window → stream SSE → save assistant message on
  `[DONE]` or error fallback on exception), and added `GET /history` and
  `DELETE /messages/{id}` endpoints. `init_db(_db_path())` is called at module
  level after `load_dotenv()`, and `HISTORY_WINDOW` is read from the environment
  with a default of 10.
- [x] **4** — Added the frontend name gate, history loading, and per-message delete buttons. Newly streamed messages receive their persistent ids via the SSE handshake so every rendered message has a working delete button.
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

### Task 3

- **File**: smoke test via Python script (`/tmp/task3_smoke.py`) using FastAPI
  `TestClient` and a mocked `generate_response`.
- **Tests run**: 16 / 16
- **Pass / fail**: 16 / 0
- **Blocker**: none

```text
PASS: GET /history unknown student returns empty list
PASS: POST /chat missing student_name returns 422
PASS: POST /chat whitespace-only name returns 400
PASS: POST /chat happy path streams SSE
PASS: POST /chat persists user then assistant
PASS: GET /history returns ordered history
PASS: DELETE own message returns 200
PASS: DELETE own message removes the targeted row
PASS: DELETE another student's message returns 403
PASS: DELETE 403 preserves the other student's row
PASS: DELETE non-existent message returns 404
PASS: Stream failure persists error fallback
PASS: No-context fallback persisted
PASS: HISTORY_WINDOW defaults to 10
PASS: GET /history missing param returns 422
PASS: DELETE missing student_name returns 422

16/16 checks passed.
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
| User message persisted before Groq call | Task 3 (`save_message` before `generate_response`) |
| Assistant message persisted after stream | Task 3 (`save_message` on `[DONE]`) |
| Stream failure persists error fallback | Task 3 (exception handler saves `ERROR_FALLBACK`) |
| No-context fallback persisted | Task 3 (buffer equals fallback is persisted as-is) |
| `GET /history` ordered full history | Task 3 (`get_history_endpoint`) |
| Unknown name returns empty history | Task 3 (`_student_id_by_name` returns `None` → `[]`) |
| `DELETE /messages/{id}` 200/403/404 semantics | Task 3 (ownership check via direct SELECT) |
| `HISTORY_WINDOW` env var default 10 | Task 3 (module-level `HISTORY_WINDOW`) |
| `init_db()` called at boot after `load_dotenv()` | Task 3 (`init_db(_db_path())` after env load) |

The frontend integration and full manual test plan will be covered by Tasks 4-6.

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
4. **Direct SQLite SELECTs in `app/main.py` for REST semantics** (Task 3): the
   `rag/history.py` module exposes CRUD helpers but does not provide
   `get_student_by_name` or `get_message_owner`. To return `{"messages": []}` for
   unknown students without creating a row, and to distinguish 403 from 404 on
   `DELETE`, `app/main.py` performs small, read-only SELECTs against the same
   SQLite file using `rag.history._db_path()` and `_configure_connection()`.
   All mutations still go through `rag/history.py`. **RESOLVED** — see the
   "Deviation Fix (post-Task 3)" section below.

## Blockers

None for Tasks 1-3. The next batch (Task 4) depends on Task 3, which is now
complete.

## Rollback Confirmation

Rolling back Tasks 1-3 requires reverting the three commits and deleting the DB
file if it exists:

```bash
git revert 9cb7d6a
git revert 58fe5aa
git revert 42d61a4
rm -f data/historial.db
```

No other modules have been modified, so no further rollback is needed.

## Out-of-Scope Check

Changes so far are limited to:

- `rag/history.py` (Task 1)
- `rag/chain.py` (Task 2)
- `app/main.py` (Task 3)
- `openspec/changes/student-history/tasks.md`
- `openspec/changes/student-history/apply-progress.md`

No changes were made to:

- `app/static/*`
- `dashboard/`
- `requirements.txt`
- `.env.example` or `AGENTS.md`

## Deviation Fix (post-Task 3)

Approved by the user before Task 4. The original Task 3 implementation reached
into `rag/history.py` private helpers (`_db_path`, `_configure_connection`) from
`app/main.py`. This fix exposes the missing read operations as public functions
and removes the private access.

### Commits

| SHA | Message |
|-----|---------|
| `ec021b0` | `feat(rag): add get_student_by_name and get_message_owner public read helpers` |
| `48eac7e` | `refactor(app): use public read helpers from rag/history.py` |

### Diff Summary

| File | Action | Δ lines |
|------|--------|---------|
| `rag/history.py` | Modified | +37 / -1 |
| `app/main.py` | Modified | +8 / -26 |
| **Total** | | **+45 / -27** |

### Before / After

| Concern | Before (Task 3) | After (fix) |
|---------|-----------------|-------------|
| Unknown student → empty history | `app/main.py` called `rag.history._db_path()` + `_configure_connection()` + `SELECT id FROM students` via `_student_id_by_name()` | `app/main.py` calls public `rag.history.get_student_by_name(display_name)` |
| DELETE 403 vs 404 | `app/main.py` called private helpers to `SELECT student_id FROM messages` | `app/main.py` calls public `rag.history.get_message_owner(message_id)` |
| `init_db()` path | `app/main.py` called `init_db(_db_path())` | `init_db()` now accepts `db_path: str \| None = None` and defaults to `_db_path()` internally; `app/main.py` calls `init_db()` |
| Private imports in `app/main.py` | `_db_path`, `_configure_connection` imported from `rag.history` | No underscore-prefixed symbols imported or called from `rag/history.py` |

### Smell Resolution Verification

```bash
$ grep -nE '_(db_path|configure_connection|student_id_by_name)' app/main.py
No underscore matches found in app/main.py
```

### Test Results

#### New helper smoke test

- **File**: `/tmp/test_history_read_helpers_smoke.py`
- **Tests run**: 4 / 4
- **Pass / fail**: 4 / 0
- **Blocker**: none

```text
PASS: get_student_by_name('Ana') returns correct id (got 1)
PASS: get_student_by_name('Ghost') returns None (got None)
PASS: get_message_owner(message_id) returns correct student_id (got 1)
PASS: get_message_owner(99999) returns None (got None)

4/4 checks passed.
```

#### Task 3 regression smoke test

- **File**: `/tmp/task3_smoke.py`
- **Tests run**: 16 / 16
- **Pass / fail**: 16 / 0
- **Blocker**: none

```text
PASS: GET /history unknown student returns empty list
PASS: POST /chat missing student_name returns 422
PASS: POST /chat whitespace-only name returns 400
PASS: POST /chat happy path streams SSE
PASS: POST /chat persists user then assistant
PASS: GET /history returns ordered history
PASS: DELETE own message returns 200
PASS: DELETE own message removes the targeted row
PASS: DELETE another student's message returns 403
PASS: DELETE 403 preserves the other student's row
PASS: DELETE non-existent message returns 404
PASS: Stream failure persists error fallback
PASS: No-context fallback persisted
PASS: HISTORY_WINDOW defaults to 10
PASS: GET /history missing param returns 422
PASS: DELETE missing student_name returns 422

16/16 checks passed
All Task 3 smoke checks passed.
```

## Next Recommended

Task 4 in the next session: add the frontend name gate, history loading, and
per-message delete buttons to `app/static/index.html`, `app/static/chat.js`, and
`app/static/style.css`.

---

# Task 4 — Frontend Name Gate, History Loading, and Delete Buttons

## Commits

| SHA | Message |
|-----|---------|
| `d3513f0` | `feat(app): expose message IDs in SSE stream` |
| `c56d840` | `feat(ui): add student name gate, history rendering, and message delete` |

## Diff Summary

| File | Action | Δ lines |
|------|--------|---------|
| `app/main.py` | Modified | +20 / -16 |
| `app/static/index.html` | Modified | +10 / -2 |
| `app/static/chat.js` | Modified | +115 / -40 |
| `app/static/style.css` | Modified | +73 / -0 |
| `tests/test_chat_sse_message_ids.py` | Created | +68 / -0 |
| **Task 4 total** | | **+286 / -58** |

> Cumulative review-budget impact: Tasks 1-3 + deviation fix + Task 4 ≈ +570 / -100
> (still below the 400-line *per-PR* budget, but the single PR is now approaching
> the threshold; the existing `single-pr-default` decision remains valid).

## Message-ID Coordination Approach

**Chosen approach: Option A** — extend the SSE stream in `app/main.py` to emit
`event: user_message_id` and `event: assistant_message_id` frames.

**Why**: The design says `app/main.py` "wraps the SSE generator" and already
intercepts the stream to persist messages. Adding two small event frames keeps the
frontend stateless (no extra polling endpoint) and is the smallest change that
satisfies the "new messages also get delete buttons" acceptance criterion.

**Frontend contract**:
- `event: user_message_id\ndata: <id>` arrives before the first assistant token.
  The frontend attaches the id to the delete button of the user message it already
  rendered.
- `event: assistant_message_id\ndata: <id>` arrives before the final
  `data: [DONE]`. The frontend attaches the id to the assistant placeholder's
  delete button before the bubble is finalized.
- `event: error` and `data: [DONE]` semantics are unchanged.

## Tasks Completed

- [x] **4** — Added the name gate, history loading, and per-message delete
  buttons to the frontend. `student_name` is read from `localStorage` on page load,
  sent in every `POST /chat`, and used to scope `GET /history` and
  `DELETE /messages/{id}`. New messages streamed during chat receive their
  persistent message ids via the SSE handshake and also get working delete
  buttons.

## Test Results

### Frontend static checks

- **File**: `app/static/index.html`
- **Command**: `rg -n 'id="name-area"|id="student-name"|id="name-submit"|disabled'`
- **Result**: all required IDs and `disabled` attributes present.

- **File**: `app/static/chat.js`
- **Command**: `node --check app/static/chat.js`
- **Result**: syntax OK.

- **Grep contract check**: `rg` confirms `name-area`, `student-name`, `name-submit`,
  `delete-btn`, `localStorage`, `student_name`, and `loadHistory` are present.

### Backend SSE handshake unit test

- **File**: `tests/test_chat_sse_message_ids.py`
- **Command**: `.venv/bin/python -m unittest tests.test_chat_sse_message_ids -v`
- **Tests run**: 1 / 1
- **Pass / fail**: 1 / 0
- **Blocker**: none

```text
test_sse_stream_exposes_user_and_assistant_message_ids ... ok

----------------------------------------------------------------------
Ran 1 test in 0.009s

OK
```

### Task 3 regression smoke test

- **File**: `/tmp/task3_smoke.py`
- **Command**: `PYTHONPATH="." .venv/bin/python /tmp/task3_smoke.py`
- **Tests run**: 16 / 16
- **Pass / fail**: 16 / 0
- **Blocker**: none

All Task 3 smoke checks passed after the SSE event-generator changes.

## SHALL Coverage (conversation-persistence spec)

| SHALL | Requirement | Covered by |
|-------|-------------|------------|
| Chat gated on typed display name | Task 4 (`#name-area`, `input.disabled`, `handleNameSubmit`) |
| Name persists across reloads | Task 4 (`localStorage` read/write) |
| `student_name` sent on every chat request | Task 4 (`sendMessage` body) |
| Frontend loads history on identification | Task 4 (`loadHistory`) |
| New messages rendered during chat get delete buttons | Task 4 + SSE id handshake |
| Single-message delete scoped to owner (UI) | Task 4 (`DELETE` with `student_name`) |

## Deviations from Design

1. **SSE message-id event names** (Task 4): the design did not specify the exact
   event names. Implementation chose `user_message_id` and `assistant_message_id`
   because they are self-describing and map 1:1 to the persistence lifecycle. The
   frontend only needs to know these two event names; the contract is documented
   here and in the apply-progress artifact.
2. **Spanish UI copy** (Task 4): the design's HTML snippet already used Spanish
   placeholder text (`"Escribí tu nombre para empezar..."`, button `"Entrar"`). The
   implementation kept that copy to match the existing Spanish chat UI. This is
   consistent with AGENTS.md §13 (language open question, default English for code,
   existing UI context is Spanish).
3. **Delete button always rendered** (Task 4): the design suggested the delete
   button "visible only on hover (or always visible — simpler for the prototype)".
   Implementation chose always-visible-but-subtle for accessibility and touch
   devices; the button is disabled until an id is assigned.

## Blockers

None. Task 4 is complete. Task 5 (config & docs) and Task 6 (manual test run) are
ready to start; they are independent of each other but both depend on Task 3.

## Rollback Confirmation

Rolling back Task 4 requires reverting the two commits above. The frontend files
and `app/main.py` are the only production code touched; `tests/test_chat_sse_message_ids.py`
can be removed or left in place (it does not depend on the frontend).


# Tasks: Student History & Basic Identification

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~301 (backend: 192, frontend: 95, docs: 14) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr-default |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All 6 tasks in one PR | Single PR to `feat/student-history` | Backend + frontend + docs tightly coupled; frontend needs new endpoints |

---

## Phase 1: Foundation — SQLite History Module

### 1. Add `rag/history.py` SQLite module

**Type**: feat
**Scope**: New module with 5 functions for student and message CRUD against SQLite. All persistence logic lives here; no other module touches `sqlite3` directly.
**Files**: `rag/history.py` (new)
**Depends on**: none

#### Acceptance criteria
- [x] `get_connection()` reads `SQLITE_PATH` from env (default `./data/historial.db`), enables WAL mode and `PRAGMA foreign_keys = ON`, returns connection
- [x] `init_db(db_path)` creates `students` and `messages` tables + index idempotently; creates `data/` dir if absent via `os.makedirs`
- [x] `get_or_create_student(display_name)` returns existing `id` on case-sensitive match, or INSERTs new row with `created_at = utcnow()` and returns new `id`
- [x] `save_message(student_id, role, content)` INSERTs a message row, returns its `id`; raises `ValueError` if role not in `('user', 'assistant')`
- [x] `get_history(student_id, limit)` returns list of dicts `{"id", "role", "content", "created_at"}` ordered by `created_at ASC, id ASC`; uses subquery for LIMIT to return last N in chronological order
- [x] `delete_message(message_id, student_id)` DELETEs only if both match, returns `True`/`False`
- [x] All timestamps are ISO 8601 UTC strings with seconds (e.g. `2026-07-21T03:15:17Z`)

**Commit**: `feat(rag): add SQLite history module with student and message tables`
**Verification**: Import in a Python REPL, call `init_db("/tmp/test.db")`, then each function. Verify with `sqlite3 /tmp/test.db ".tables"` and `.schema`.

---

## Phase 2: Core — History Injection into RAG Chain

### 2. Add `history` parameter to `rag/chain.py`

**Type**: feat
**Scope**: `generate_response` accepts an optional `history` list and injects it between `_FEW_SHOT` and the current query. A dev-mode log gate prints the assembled message list for manual review.
**Files**: `rag/chain.py` (modify)
**Depends on**: Task 1

#### Acceptance criteria
- [x] `generate_response` signature gains `history: list[dict] | None = None` parameter
- [x] When `history` is truthy, messages list is `[system, *_FEW_SHOT, *history, {user: query}]`
- [x] When `history` is `None` or `[]`, messages list is identical to the current single-turn shape
- [x] Dev-mode gate: when `PRODUCTION` env var is unset, assembled messages are printed to stdout with index, role, and 80-char content preview
- [x] `_FEW_SHOT` content and order are byte-for-byte unchanged
- [x] System prompt is unchanged
- [x] `generate_response` remains a pure generator — no SQLite calls, no I/O side effects

**Commit**: `feat(rag): inject conversation history into Groq messages list`
**Verification**: Start backend in dev mode, send a query, inspect console output for `[MSG 00] system | ...`, `[MSG 01] user | ...` (few-shot), then history entries, then current query.

---

## Phase 3: Integration — FastAPI Endpoints & Persistence Lifecycle

### 3. Add endpoints and persistence lifecycle to `app/main.py`

**Type**: feat
**Scope**: Three changes to `app/main.py`: (a) `ChatRequest` gains `student_name`, (b) `POST /chat` wraps the generator with persistence lifecycle, (c) two new endpoints `GET /history` and `DELETE /messages/{id}`. Boot-time `init_db()` call.
**Files**: `app/main.py` (modify)
**Depends on**: Task 1, Task 2

#### Acceptance criteria
- [x] `ChatRequest` model adds `student_name: str = Field(..., min_length=1)`
- [x] `POST /chat` validates `student_name.strip()` is non-empty → 400 if blank
- [x] `POST /chat` calls `get_or_create_student` → `save_message(user)` → `get_history(limit=HISTORY_WINDOW)` → `generate_response(query, chunks=None, history=history)` (retrieval stays inside chain)
- [x] `POST /chat` wraps the SSE generator: streams tokens to client while accumulating buffer; on `[DONE]` calls `save_message(assistant, buffer)`; on exception calls `save_message(assistant, ERROR_FALLBACK)`
- [x] `GET /history?student_name=...` returns `{"messages": [...]}` with full ordered history; returns `{"messages": []}` for unknown names; returns 422 if param missing
- [x] `DELETE /messages/{id}?student_name=...` returns 200 on success, 403 if message exists but belongs to another student, 404 if not found
- [x] `init_db()` called at module level during boot (after `load_dotenv()`)
- [x] `HISTORY_WINDOW` read from env with default `10`

**Commit**: `feat(app): add student history endpoints and persistence lifecycle`
**Verification**: `curl` each endpoint. Verify SQLite rows with `sqlite3 data/historial.db "SELECT * FROM messages"`. Test 403 by deleting another student's message.

---

## Phase 4: Frontend — Name Gate, History Rendering, Delete Buttons

### 4. Add name input, history loading, and delete buttons to frontend

**Type**: feat
**Scope**: Three frontend files gain: (a) name input gating the chat, (b) `localStorage` persistence for the name, (c) history rendering on page load, (d) per-message delete buttons, (e) `student_name` in every `POST /chat` request body.
**Files**: `app/static/index.html` (modify), `app/static/chat.js` (modify), `app/static/style.css` (modify)
**Depends on**: Task 3

#### Acceptance criteria
- [x] `index.html`: name input area (`#name-area`) with `#student-name` input and `#name-submit` button appears above `#chat-form`; chat input starts `disabled`
- [x] `chat.js`: on name submit (click or Enter), stores name in `localStorage`, hides name area, enables chat input, calls `loadHistory()`
- [x] `chat.js`: on page load, if `localStorage.student_name` exists, skips name area and calls `loadHistory()`
- [x] `chat.js`: `loadHistory()` fetches `GET /history?student_name=...` and renders each message with a delete button (`<button class="delete-btn" data-message-id="..."></button>`)
- [x] `chat.js`: `sendMessage` includes `student_name` in the `POST /chat` body
- [x] `chat.js`: delete button click handler sends `DELETE /messages/{id}?student_name=...`; on 200 removes the `.message` element from DOM; on 403/404 silently ignores
- [x] `chat.js`: new messages rendered during chat also get delete buttons (with `data-message-id` from the response — requires backend to return message IDs in SSE or a follow-up)
- [x] `style.css`: `.name-area`, `#student-name`, `#name-submit` styled consistently with existing input area; `.delete-btn` is a small `×` positioned in the message bubble corner

**Commit**: `feat(ui): add student name gate, history rendering, and message delete`
**Verification**: Open in browser. Fresh visit shows name input. Type name, chat enables. Send message, see it persisted. Reload page, history loads. Click × on a message, it disappears.

---

## Phase 5: Configuration & Documentation

### 5. Update `.env.example` and `AGENTS.md`

**Type**: docs
**Scope**: Document the new `HISTORY_WINDOW` env var and the architectural decisions (typed-name auth, HF Spaces sleep trade-off) so future developers and reviewers have context.
**Files**: `.env.example` (modify), `AGENTS.md` (modify)
**Depends on**: Task 3

#### Acceptance criteria
- [x] `.env.example` adds `HISTORY_WINDOW=10` with a comment explaining its purpose and that `0` disables injection
- [x] `.env.example` adds `PRODUCTION` (commented out) with a note that setting it suppresses the dev-mode message dump
- [x] `AGENTS.md` §7 (Architecture Decisions) adds a new entry documenting the typed-name auth decision and its trade-offs (name collisions, no logout)
- [x] `AGENTS.md` §7 adds a note about HF Spaces ephemeral disk losing history on sleep (accepted trade-off, references proposal decision 5)
- [x] `AGENTS.md` §12 (Environment Variables) adds `HISTORY_WINDOW` and `PRODUCTION` rows

**Commit**: `docs: document history window config and typed-name auth trade-offs`
**Verification**: Read both files. Confirm new entries are present and accurate.

---

## Phase 6: Verification — Manual Test Execution

### 6. Execute 10 manual test cases and record results

**Type**: test
**Scope**: Run the 10 test cases from the design document's Test Plan section. Record pass/fail for each in a dated results file.
**Files**: `tests/student_history_run_<YYYY-MM-DD>.md` (new)
**Depends on**: Task 1, Task 2, Task 3, Task 4, Task 5

#### Acceptance criteria
- [x] Test 1: Fresh visit → name gate visible, chat input disabled
- [x] Test 2: Name submission enables chat, `localStorage` populated
- [x] Test 3: History loaded on page load (pre-seed SQLite, reload, verify rendering)
- [x] Test 4: Multi-turn chat — second response references first turn (verify via console `[MSG]` dump)
- [x] Test 5: Delete own user message — row removed from SQLite, UI updates
- [x] Test 6: Delete assistant message — row removed, UI reflows (standard chat UX; design.md updated from original "gap visible" to match the implementation)
- [x] Test 7: Cross-student delete returns 403, message preserved
- [x] Test 8: Unknown name → `GET /history` returns `{"messages": []}`
- [x] Test 9: Survive backend restart — history persists in SQLite, visible after reload
- [x] Test 10: `HISTORY_WINDOW=0` disables injection — console shows no history entries in messages list
- [x] Results file created at `tests/student_history_run_<YYYY-MM-DD>.md` with pass/fail per test and notes on any failures

**Commit**: `test: record manual test run for student-history (10 cases)`
**Verification**: Open the results file. All 10 cases marked PASS. Any failures documented with reproduction steps.

---

## Implementation Order

```
Task 1 (rag/history.py)
  └→ Task 2 (rag/chain.py)
       └→ Task 3 (app/main.py)
            ├→ Task 4 (frontend)
            └→ Task 5 (config & docs)
                 └→ Task 6 (manual tests)
```

Tasks 4 and 5 are independent of each other and can be done in either order, but both depend on Task 3. Task 6 depends on all prior tasks.

## Dependency Graph

```
1 ──→ 2 ──→ 3 ──→ 4 ──→ 6
                └→ 5 ──→ 6
```

- Task 1: no dependencies
- Task 2: depends on 1
- Task 3: depends on 1, 2
- Task 4: depends on 3
- Task 5: depends on 3
- Task 6: depends on 1, 2, 3, 4, 5

## Commit Boundaries

Each task maps to exactly one commit. No task should be split across commits, and no two tasks should be combined into one commit. The commit messages follow conventional-commits format.

**Exception**: Task 4 touches 3 files but they form a single logical unit (frontend history feature). One commit is correct.

## Line Count Estimates (per file)

| File | Type | Est. Lines |
|------|------|-----------|
| `rag/history.py` | new | ~95 |
| `rag/chain.py` | modify | ~14 |
| `app/main.py` | modify | ~83 |
| `app/static/index.html` | modify | ~10 |
| `app/static/chat.js` | modify | ~55 |
| `app/static/style.css` | modify | ~30 |
| `.env.example` | modify | ~4 |
| `AGENTS.md` | modify | ~10 |
| `tests/student_history_run_*.md` | new | ~40 (not in review budget) |
| **Total (review budget)** | | **~301** |

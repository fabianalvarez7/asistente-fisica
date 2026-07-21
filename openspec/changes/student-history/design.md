# Design: Student History & Basic Identification

## Technical Approach

Add two tightly coupled capabilities to the existing single-turn RAG chat: (1) typed-name student identification persisted in `localStorage`, and (2) SQLite-backed conversation history injected into the Groq `messages` list between `_FEW_SHOT` and the current query. The change is **additive**: the Socratic prompt, few-shot examples, RAG retrieval, and SSE streaming are all preserved unchanged. A new `rag/history.py` module handles all SQLite operations using `sqlite3` stdlib. The FastAPI layer gains two endpoints (`GET /history`, `DELETE /messages/{id}`) and extends `POST /chat` to accept `student_name` and orchestrate the persistence lifecycle. The frontend adds a name input (gating the chat), loads history on page load, and renders per-message delete buttons.

This design resolves all 5 risks left open by sdd-spec: DELETE auth shape, case-sensitivity, timestamp granularity, the manual review step, and the error fallback locale.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| History injection position | After `_FEW_SHOT`, before current query | Before `_FEW_SHOT` (dilutes few-shot pattern) | System → few-shot → history → query is standard multi-turn LLM ordering. The few-shot pattern is seen fresh by the model before the conversation context. |
| Persistence boundary | `app/main.py` persists; `rag/chain.py` does NOT | `rag/chain.py` writes to SQLite | Keeps `chain.py` a pure generator with no I/O side effects. FastAPI is the orchestrator — it calls the chain, accumulates the stream, and persists. This is the existing architectural rule (AGENTS.md §5). |
| DELETE auth shape | `student_name` as query param (`?student_name=...`) | Body field, header | Simpler — no body needed for DELETE, matches REST convention for scoping. The handler validates ownership by joining `messages.student_id` with `students.id` filtered by `display_name`. |
| `created_at` type | `TEXT NOT NULL` — ISO 8601 UTC string with seconds (`2026-07-21T03:15:17Z`) | SQLite `TIMESTAMP` (synonym for TEXT) or Unix epoch integer | Explicit ISO 8601 is human-readable for debugging. Second granularity resolves the spec's tiebreak concern: two messages in the same second share `created_at`, but `ORDER BY id ASC` as secondary sort breaks the tie deterministically. |
| Transaction strategy | Autocommit per operation via `sqlite3.connect` context manager | Explicit `BEGIN/COMMIT` | Prototype scale — no concurrent writers. The `with` block guarantees connection close. For the `POST /chat` path, the user message write and assistant message write are independent commits (user message is safe even if Groq fails). |
| History window default | N=10, configurable via `HISTORY_WINDOW` | N=20 (safer context) or N=5 (tighter) | 10 turns = 20 messages × ~150 tokens = ~3000 tokens — well within budget. Configurable via env var lets Nair/Fabián tune without code changes. |
| No unique constraint on `display_name` | Exact case-sensitive match, collisions merge histories | Unique constraint (rejects second "Ana") | Accepted trade-off per proposal. Two students with the same exact name share a thread. If this becomes a problem, a future change adds a disambiguation step (e.g., "Ana (2)"). |

## Data Flow

```
Browser                        FastAPI                    SQLite              Groq
  │                               │                         │                  │
  │ 1. Name input → localStorage   │                         │                  │
  │                               │                         │                  │
  │ 2. GET /history?student_name=… │                         │                  │
  │ ─────────────────────────────→ │ 3. SELECT messages      │                  │
  │                               │ ──────────────────────→ │                  │
  │ 4. Render history              │ ←────────────────────── │                  │
  │ ←───────────────────────────── │                         │                  │
  │                               │                         │                  │
  │ 5. POST /chat {student_name, query}                      │                  │
  │ ─────────────────────────────→ │ 6. get_or_create_student│                  │
  │                               │ ──────────────────────→ │                  │
  │                               │ 7. save_message(user)    │                  │
  │                               │ ──────────────────────→ │                  │
  │                               │ 8. get_history(N)        │                  │
  │                               │ ──────────────────────→ │                  │
  │                               │                         │                  │
  │                               │ 9. generate_response(query, chunks, history)    │
  │                               │ ──────────────────────────────────────────────→ │
  │ 10. SSE stream (tokens)       │ ←────────────────────────────────────────────── │
  │ ← - - - - - - - - - - - - - - │                         │                  │
  │                               │ 11. accumulate buffer   │                  │
  │                               │ 12. save_message(asst)  │                  │
  │                               │ ──────────────────────→ │                  │
  │                               │                         │                  │
  │ 13. DELETE /messages/42?student_name=Ana                 │                  │
  │ ─────────────────────────────→ │ 14. verify ownership    │                  │
  │                               │ ──────────────────────→ │                  │
  │                               │ 15. DELETE WHERE id=42   │                  │
  │ 16. 200 / 403 / 404           │ ──────────────────────→ │                  │
  │ ←───────────────────────────── │                         │                  │
```

**Error paths** (not shown):
- Groq stream failure: user message already at step 7; step 12 persists `"Ocurrió un error, intentá de nuevo"` as assistant fallback.
- No-context (cosine > 0.5): `chain.py` short-circuits as today; step 12 persists the hardcoded `"No encuentro info sobre esto en los apuntes"`.
- DELETE for non-owned message: step 14 fails → 403; no row removed.

## Data Model

```sql
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL  -- ISO 8601 UTC, e.g. "2026-07-21T03:15:17Z"
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL  -- ISO 8601 UTC, same format as students.created_at
);

CREATE INDEX IF NOT EXISTS idx_messages_student_created
    ON messages(student_id, created_at);
```

- **Why `TEXT` for timestamps**: human-readable for `sqlite3` CLI debugging. ISO 8601 with seconds is sortable as a string (`ORDER BY created_at ASC` works correctly) and resolves the spec's tiebreak concern: two messages in the same second are ordered secondarily by `id ASC`.
- **Why no `conversations` table**: proposal decision 2 — one thread per student for the prototype.
- **Case-sensitive exact match**: `WHERE display_name = ?` in SQLite is case-sensitive by default. "Ana" ≠ "ana". This is a known trade-off — a student who types their name differently on a second device creates a new student row and orphaned history.
- **No foreign key pragma enforcement**: SQLite requires `PRAGMA foreign_keys = ON` per connection. The `get_connection()` helper in `history.py` enables it.

## New Module: `rag/history.py`

All functions use `sqlite3` stdlib. No SQLAlchemy (prototype constraint, AGENTS.md §7 decision 7). The module-level `get_connection()` helper opens `SQLITE_PATH` from the environment, enables WAL mode and foreign keys, and returns the connection. All public functions accept it as a parameter or create one internally.

```python
def init_db(db_path: str) -> None:
    """Create tables and indexes if they don't exist. Idempotent.
    
    Called once at backend startup. Creates the `data/` directory if absent.
    """
    ...

def get_or_create_student(display_name: str) -> int:
    """Return the `id` of the first row matching `display_name` (case-sensitive).
    
    If no match, INSERT a new row with `created_at = utcnow()` and return the
    new `id`. Raises `sqlite3.Error` on connection failure.
    """
    ...

def save_message(student_id: int, role: str, content: str) -> int:
    """INSERT a row into `messages` and return its `id`.
    
    `role` must be 'user' or 'assistant'.
    `created_at` is set to `utcnow()` — NOT the request time.
    Raises `ValueError` if role is invalid; `sqlite3.IntegrityError` if
    `student_id` does not exist.
    """
    ...

def get_history(student_id: int, limit: int | None = None) -> list[dict]:
    """Return messages for `student_id`, ordered by `created_at` ASC, `id` ASC.
    
    Each dict: `{"id": int, "role": str, "content": str, "created_at": str}`.
    If `limit` is provided, returns only the LAST `limit` rows (using a
    subquery: `ORDER BY created_at DESC LIMIT N`, then re-sort ASC).
    Returns empty list if the student has no messages.
    """
    ...

def delete_message(message_id: int, student_id: int) -> bool:
    """DELETE the message with `id = message_id` AND `student_id = student_id`.
    
    Returns `True` if a row was deleted, `False` if no matching row existed.
    Does NOT cascade-delete paired messages (one row at a time, per spec).
    """
    ...
```

**Design notes**:
- `get_history` uses a subquery for the LIMIT: `SELECT * FROM (SELECT ... ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC`. This returns the last N messages in chronological order.
- `get_or_create_student` is NOT protected by a unique constraint; it does a SELECT then INSERT. For the prototype's single-writer model, this is safe. If concurrent writes become a concern, switch to `INSERT OR IGNORE` with a unique constraint.
- `init_db` calls `os.makedirs(os.path.dirname(db_path), exist_ok=True)` before connecting, satisfying the spec's auto-create-directory requirement.

## Modified: `rag/chain.py`

### Signature change

```python
def generate_response(
    query: str,
    context_chunks: list[str],
    history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """...existing docstring...

    New parameters:
      - history: list of {"role": ..., "content": ...} dicts from SQLite,
        ordered chronologically. None or [] means no history (single-turn).
        Injected between _FEW_SHOT and the current query.
    """
```

### Messages construction change

```python
messages = [{"role": "system", "content": prompt}]
messages.extend(_FEW_SHOT)
if history:
    messages.extend(history)
messages.append({"role": "user", "content": query})
```

### Manual review gate

Per the spec's requirement for human-verifiable ordering, in dev mode (when no `PRODUCTION` env var is set), the assembled `messages` list SHALL be printed or logged before the Groq call:

```python
if not os.getenv("PRODUCTION"):
    # Manual review gate: dump assembled message list for eyeball verification.
    for i, msg in enumerate(messages):
        role = msg["role"]
        preview = msg["content"][:80].replace("\n", " ")
        print(f"[MSG {i:02d}] {role:9s} | {preview}...")
```

This is a manual gate, not an automated test. A reviewer runs the backend in dev mode, submits a query, and inspects the console output to verify the ordering is `system → few-shot → history → query`.

### Error fallback contract

`generate_response` does NOT persist anything. It is a pure generator. The caller (`app/main.py`) is responsible for:
1. Persisting the user message BEFORE calling `generate_response`.
2. Accumulating the SSE stream into a buffer.
3. Persisting the full assistant message on `[DONE]`.
4. On exception, persisting `"Ocurrió un error, intentá de nuevo"` as the assistant message.

### No-context fallback contract

When `cosine > 0.5`, `generate_response` yields `data: No encuentro info sobre esto en los apuntes\n\n` then `data: [DONE]\n\n` (existing behavior, unchanged). The caller detects this by checking if the buffer content equals the hardcoded fallback phrase, and persists accordingly. Alternative: the caller always persists the buffer as the assistant message — the fallback phrase is just a special case of a valid assistant response.

**Design choice**: the caller always persists the buffer content as-is. The chain yields what it yields; the caller is a dumb accumulator. This keeps the boundary clean — `chain.py` knows nothing about persistence.

## Modified: `app/main.py`

### `ChatRequest` model

```python
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    student_name: str = Field(
        ...,
        min_length=1,
        description="Display name typed by the student. Required — no anonymous chat."
    )
```

Pydantic's `min_length=1` rejects empty strings. Whitespace-only strings like `"   "` pass Pydantic validation (min_length is character count, not trimmed), so the endpoint adds an explicit `student_name.strip()` check and returns 400 if empty after stripping.

### `POST /chat` — modified

```
1. Validate student_name: reject if empty or whitespace-only → 400.
2. student_id = get_or_create_student(student_name)
3. history = get_history(student_id, limit=HISTORY_WINDOW)
4. save_message(student_id, "user", query)
5. chunks = retrieve(query)  -- existing RAG retrieval, unchanged
6. buffer = ""
7. for token in generate_response(query, chunks, history):
       yield token
       buffer += extract_data(token)
8. On [DONE]: save_message(student_id, "assistant", buffer)
9. On exception: save_message(student_id, "assistant", ERROR_FALLBACK)
```

The existing `StreamingResponse(generate_response(...))` pattern changes: the endpoint now wraps the generator to accumulate the buffer. The SSE frames are still streamed to the client as they arrive (no buffering on the wire — only the accumulated string for final persistence).

### `GET /history?student_name=...` — new

```python
@app.get("/history")
async def get_history_endpoint(student_name: str):
    """Return all messages for a student, ordered by created_at ASC.
    
    Returns [] if the student doesn't exist (row created lazily on first POST /chat).
    Returns 400 if student_name is missing or empty.
    """
```

Response shape:
```json
{
  "messages": [
    {"id": 1, "role": "user", "content": "¿cómo resuelvo esto?", "created_at": "2026-07-21T03:15:17Z"},
    {"id": 2, "role": "assistant", "content": "Pensá en qué principio...", "created_at": "2026-07-21T03:15:25Z"}
  ]
}
```

### `DELETE /messages/{message_id}?student_name=...` — new

```python
@app.delete("/messages/{message_id}")
async def delete_message_endpoint(message_id: int, student_name: str):
    """Delete a message. Returns 200 on success, 403 if not owned, 404 if not found."""
```

Ownership check: `SELECT messages.id FROM messages JOIN students ON messages.student_id = students.id WHERE messages.id = ? AND students.display_name = ?`. If no row → 404. If row exists but `display_name` doesn't match → the JOIN returns no row → also 404. The 403 case requires a two-step check: first verify the message exists (any owner), then verify the owner matches. If the message exists but belongs to a different student → 403.

## Modified: Frontend (`app/static/*`)

### `index.html`

Add BEFORE the `<form id="chat-form">`:

```html
<div id="name-area" class="name-area">
  <input
    id="student-name"
    type="text"
    autocomplete="off"
    placeholder="Escribí tu nombre para empezar..."
    aria-label="Nombre"
  />
  <button type="button" id="name-submit">Entrar</button>
</div>
```

The `#chat-form` input starts with the `disabled` attribute. It is enabled by JS after name submission.

### `chat.js`

**New globals and init**:
```javascript
const nameArea = document.getElementById('name-area');
const nameInput = document.getElementById('student-name');
const nameSubmit = document.getElementById('name-submit');
const STORAGE_KEY = 'student_name';
let studentName = localStorage.getItem(STORAGE_KEY);
```

**Name submission**:
```javascript
nameSubmit.addEventListener('click', () => {
  const name = nameInput.value.trim();
  if (!name) return;
  localStorage.setItem(STORAGE_KEY, name);
  studentName = name;
  nameArea.style.display = 'none';
  input.disabled = false;
  sendBtn.disabled = false;
  loadHistory();
});
// Also handle Enter key on nameInput
```

**History loading**:
```javascript
async function loadHistory() {
  const resp = await fetch(`/history?student_name=${encodeURIComponent(studentName)}`);
  const data = await resp.json();
  for (const msg of data.messages) {
    renderMessage(msg);  // reuses existing appendUserMessage pattern, plus new appendAssistantMessage
  }
}
```

**Render with delete buttons**: each rendered message gets a `<button class="delete-btn" data-message-id="...">×</button>`. Click handler:

```javascript
messages.addEventListener('click', async (e) => {
  if (!e.target.classList.contains('delete-btn')) return;
  const msgId = e.target.dataset.messageId;
  const resp = await fetch(`/messages/${msgId}?student_name=${encodeURIComponent(studentName)}`, { method: 'DELETE' });
  if (resp.ok) {
    e.target.closest('.message').remove();
  } // 403/404 → silent ignore (UI stays)
});
```

**`sendMessage` modification**: the `fetch('/chat', ...)` body changes from `{ query }` to `{ query, student_name: studentName }`.

**On page load**: if `studentName` exists → hide `nameArea`, enable chat, call `loadHistory()`. If not → show `nameArea`, disable chat.

### `style.css`

New rules for `.name-area`, `#student-name`, `#name-submit`, `.delete-btn`. The delete button is a small `×` positioned in the top-right corner of each message bubble, visible only on hover (or always visible — simpler for the prototype).

## Configuration

| Variable | Default | Added/Existing | Purpose |
|----------|---------|----------------|---------|
| `SQLITE_PATH` | `./data/historial.db` | Existing (`.env.example:15`) | Path to SQLite DB. Code now reads it. |
| `HISTORY_WINDOW` | `10` | **New** | Number of recent messages to inject into Groq. Set to 0 to disable history injection. |
| `PRODUCTION` | unset | **New** | If set, suppresses the manual review `print()` gate in `chain.py`. |

Add to `.env.example`:

```
# Cantidad de mensajes recientes inyectados en el prompt de Groq
# 0 = desactivar inyección de historial
HISTORY_WINDOW=10
```

## Error Handling Matrix

| Case | HTTP | Body | Frontend behavior |
|------|------|------|-------------------|
| Missing `student_name` in `POST /chat` | 400 | `{"detail": "student_name is required"}` (Pydantic) | N/A — frontend always sends it from localStorage |
| Whitespace-only `student_name` | 400 | `{"detail": "student_name cannot be empty"}` | Show error in hint area |
| `GET /history` with unknown name | 200 | `{"messages": []}` | Empty chat UI (no messages rendered) |
| `GET /history` missing `student_name` param | 422 | FastAPI validation error | N/A — frontend always sends it |
| `DELETE /messages/{id}` for non-owned message | 403 | `{"detail": "not authorized"}` | Silent ignore (message stays) |
| `DELETE /messages/{id}` for non-existent id | 404 | `{"detail": "message not found"}` | Silent ignore |
| `DELETE /messages/{id}` missing `student_name` | 422 | FastAPI validation error | N/A |
| Groq stream failure | 200 (SSE) | Error frame then `[DONE]` | Assistant bubble shows `"Ocurrió un error, intentá de nuevo"` (existing behavior, unchanged) |
| SQLite write failure | 500 | `{"detail": "internal error"}` | Frontend shows generic error in hint |
| ChromaDB empty at boot | — | FastAPI raises RuntimeError before starting | Server won't start (existing behavior, unchanged) |

## Rollout & Migration

- **Schema auto-creates** on first `init_db()` call (backend startup). No migration tool. `CREATE TABLE IF NOT EXISTS` is idempotent.
- **Existing `data/` directory**: already exists (contains `chroma/` and `pdfs/`). `init_db` creates `historial.db` inside it. If `historial.db` already exists from a prior prototype run, `CREATE TABLE IF NOT EXISTS` is a no-op — safe.
- **HF Spaces deploy**: the `data/` directory is writable (confirmed in `deploy-hf-spaces` explore). No new deploy steps. Ephemeral disk means history is lost on sleep (~48h) — this is an accepted trade-off (proposal decision 5, AGENTS.md §7 decision 8).
- **Rollback**:
  ```bash
  git revert <commit-hash>
  rm data/historial.db              # delete the DB file
  # Remove HISTORY_WINDOW from .env if it was added
  ```
  No model swap, no embedding re-bake. The Socratic layer, RAG retrieval, and frontend chat are untouched.

## Test Plan (manual, 8-10 cases, <15 min)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Fresh visit → name gate | Open app in incognito. | Name input visible, chat input disabled. |
| 2 | Name submission enables chat | Type "Ana", click "Entrar". | Chat enabled, name area hidden, `localStorage.student_name = "Ana"`. |
| 3 | History loaded on page load | Pre-seed "Ana" with 3 messages in SQLite. Reload page. | 3 messages rendered in chat UI before any new message. |
| 4 | Multi-turn chat | Send "¿qué es la aceleración?". Then "¿y cómo se calcula?". | Second response references acceleration (the model saw the first turn). Verify via server console: the assembled messages list includes both prior turns. |
| 5 | Delete own message | Click × on a user message. | Message disappears from UI. SQLite row removed. |
| 6 | Delete assistant message | Click × on an assistant message. | Message disappears. Gap visible. |
| 7 | Cross-student delete (403) | Open incognito → "Beto". Use browser dev tools to `DELETE /messages/42?student_name=Beto` where message 42 belongs to "Ana". | 403 response. Message 42 still in DB. |
| 8 | Unknown name → empty history | Navigate to `GET /history?student_name=Nobody`. | 200 with `{"messages": []}`. |
| 9 | Survive backend restart | Send 2 messages. Kill uvicorn. Relaunch. Reload page. | History still visible (durable in DB, not in-memory). |
| 10 | `HISTORY_WINDOW=0` disables injection | Set env var, restart, send query. | Console shows: no history entries in the injected messages list. Same as single-turn behavior. |

**Note**: test 10 also serves as the regression gate — setting `HISTORY_WINDOW=0` restores the exact single-turn message list that existed before this change.

## Skill Resolution

- `sdd-design` — loaded (main skill)
- `_shared/sdd-phase-common` — loaded via sdd-design reference
- `_shared/sdd-status-contract` — loaded via sdd-phase-common reference
- `_shared/openspec-convention` — loaded via sdd-phase-common reference

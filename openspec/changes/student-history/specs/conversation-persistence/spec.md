# conversation-persistence Specification

## Purpose

Persistent, per-student conversation history for the chat prototype. All user and assistant messages are written to a SQLite file (`data/historial.db`). The schema auto-initializes on first backend startup. Messages are persisted around the Groq call so a crash mid-stream leaves a recoverable state. The frontend loads history on identification and can delete individual messages from the student's own thread. The last N messages (default 10) are injected into the Groq `messages` list between `_FEW_SHOT` and the current query, giving the model conversational context it did not have before.

## Requirements

### Requirement: SQLite schema for students and messages

The persistence layer SHALL store history in two SQLite tables, created on first backend startup via `CREATE TABLE IF NOT EXISTS`:

| Table | Columns | Notes |
|-------|---------|-------|
| `students` | `id` (PK), `display_name` (TEXT, no unique constraint), `created_at` (timestamp) | One row per typed name (case-sensitive). Collisions merge. |
| `messages` | `id` (PK), `student_id` (FK → `students.id`), `role` (`user` \| `assistant`), `content` (TEXT), `created_at` (timestamp) | Ordered by `created_at` for history retrieval. |

There SHALL be no conversation/table (one thread per student — proposal decision 2) and no session, password, or token tables.

#### Scenario: First startup creates tables

- GIVEN `data/historial.db` does not exist
- WHEN the backend boots
- THEN the file is created and both tables exist (inspection via `sqlite3` shows `students` and `messages`)

#### Scenario: Subsequent startup is idempotent

- GIVEN `data/historial.db` already exists with data
- WHEN the backend boots again
- THEN no tables are recreated and existing rows are preserved

### Requirement: Persistence lifecycle around the Groq call

For each `POST /chat` request, the backend SHALL persist the user message to SQLite BEFORE calling Groq (so a Groq failure still leaves the student's question on record). The assistant message SHALL be persisted AFTER the stream completes, using the full concatenated response. On stream failure mid-way, the backend SHALL persist an assistant message with the exact content `"Ocurrió un error, intentá de nuevo"`. Both messages SHALL carry the `created_at` of insertion (not the request time).

#### Scenario: Happy path persists user then assistant

- GIVEN student "Ana" sends "¿cómo resuelvo este problema?"
- WHEN Groq streams a complete response "Pensá en qué principio..."
- THEN a `user` message with "¿cómo resuelvo este problema?" exists in SQLite
- AND an `assistant` message with "Pensá en qué principio..." exists in SQLite
- AND the `user` row has an earlier `created_at` than the `assistant` row

#### Scenario: Groq failure leaves a fallback assistant message

- GIVEN student "Ana" sends a valid query
- WHEN the Groq stream raises an exception or the connection drops mid-stream
- THEN a `user` message with her query is present in SQLite
- AND an `assistant` message with content "Ocurrió un error, intentá de nuevo" is present in SQLite
- AND no partial model output is persisted as the assistant message

#### Scenario: User message persisted even before persistence layer error

- GIVEN SQLite write of the user message succeeds but a later error occurs before the model is called
- WHEN the request fails before reaching Groq
- THEN the student's question is still present in SQLite under her `student_id`
- AND the chat response to the client reflects the failure (no assistant fabrication)

### Requirement: No-context fallback is also persisted

When the retriever returns no usable context (cosine distance > 0.5 per existing `rag-grounding` rule) and the assistant falls back to the hardcoded phrase `"No encuentro info sobre esto en los apuntes"`, the backend SHALL persist the user message AND persist that exact fallback string as the assistant message. The persistence path is identical to the happy path; only the assistant content differs.

#### Scenario: Out-of-corpus query still leaves history

- GIVEN student "Ana" asks a question that retrieves no in-corpus context
- WHEN the no-context fallback fires
- THEN a `user` message with her query is present in SQLite
- AND an `assistant` message with content "No encuentro info sobre esto en los apuntes" is present in SQLite

### Requirement: History retrieval endpoint

The backend SHALL expose `GET /history?student_name={name}` returning a JSON array of all messages for the student identified by `display_name = {name}`, ordered by `created_at` ascending. Each element SHALL contain `id`, `role`, `content`, and `created_at`. If no student exists for the name, the endpoint SHALL return an empty array (not 404) — the student row will be created lazily on the next `POST /chat`. If `student_name` is missing or empty, the endpoint SHALL return 4xx.

#### Scenario: Existing student returns full ordered history

- GIVEN student "Ana" has 4 messages persisted over time
- WHEN the frontend calls `GET /history?student_name=Ana`
- THEN the response is 200 with a JSON array of length 4
- AND the array is ordered so element `i` has `created_at` ≤ element `i+1`
- AND each element exposes `id`, `role`, `content`, `created_at`

#### Scenario: Unknown name returns empty list

- GIVEN no `students` row has `display_name = "Lucía"`
- WHEN `GET /history?student_name=Lucía` is called
- THEN the response is 200 with `[]`

#### Scenario: Missing name parameter is rejected

- GIVEN the frontend calls `GET /history` with no `student_name` query parameter
- WHEN the request reaches the backend
- THEN the backend responds 4xx
- AND no database read is performed

### Requirement: Single-message deletion scoped to the owning student

The backend SHALL expose `DELETE /messages/{id}` which removes the message row with primary key `id`. The endpoint SHALL verify the message exists and that its `student_id` corresponds to a `display_name` matching the `student_name` supplied in the request (e.g., as a query param or body field). If the message does not exist, return 404. If the message exists but belongs to a different student, return 403. The endpoint SHALL NOT delete assistant messages that were paired with the deleted user message; deletion is single-row and leaves gaps (per proposal §Edit Semantics).

#### Scenario: Student deletes own message

- GIVEN student "Ana" sends `DELETE /messages/42` with `student_name=Ana`
- WHEN message 42 exists and belongs to Ana
- THEN the message is removed from SQLite
- AND the endpoint returns 200 (or 204)
- AND the frontend re-renders history without message 42

#### Scenario: Student cannot delete another's message

- GIVEN student "Ana" sends `DELETE /messages/42` with `student_name=Ana`
- WHEN message 42 exists but belongs to student "Bruno"
- THEN the endpoint returns 403
- AND message 42 is still in SQLite

#### Scenario: Deleting a non-existent message

- GIVEN any student sends `DELETE /messages/9999` and no message with id 9999 exists
- WHEN the request reaches the backend
- THEN the endpoint returns 404
- AND no row is removed

#### Scenario: Missing `student_name` on DELETE is rejected

- GIVEN a `DELETE /messages/42` request without `student_name`
- WHEN the request reaches the backend
- THEN the endpoint returns 4xx
- AND the row is not removed

### Requirement: History injection into the Groq `messages` list

The RAG chain (`rag/chain.py`) SHALL inject the student's last N messages into the Groq `messages` list, positioned between `_FEW_SHOT` and the current query:

```
messages = [system] + _FEW_SHOT + history + [current_query]
```

`history` SHALL be a list of `{"role": "user"|"assistant", "content": "..."}` dicts fetched from SQLite ordered by `created_at` ascending, truncated to the last N. N (the window size) SHALL default to 10 and SHALL be configurable via the `HISTORY_WINDOW` environment variable. The system prompt and `_FEW_SHOT` order and content SHALL be unchanged relative to the existing Socratic layer. The injection SHALL be additive: removing it (N=0) restores the prior single-turn message list.

#### Scenario: Default window of 10 is injected

- GIVEN `HISTORY_WINDOW` is unset and student "Ana" has 14 prior messages
- WHEN Ana sends a new query
- THEN the `messages` list sent to Groq contains `[system, ...few_shot..., <last 10 of Ana's messages>, current_query]`
- AND the 10 injected items are ordered chronologically (oldest first)

#### Scenario: Window is configurable via env var

- GIVEN `HISTORY_WINDOW=2` is set in the environment
- WHEN Ana sends a query
- THEN only the last 2 of her messages are injected (plus `current_query`)

#### Scenario: Empty history yields no injection

- GIVEN student "Lucía" has zero persisted messages
- WHEN Lucía sends her first query
- THEN the `messages` list is `[system, ...few_shot..., current_query]` — identical in shape to the single-turn baseline

#### Scenario: Order and content of system/few-shot preserved

- GIVEN the Socratic system prompt and the existing `_FEW_SHOT` examples
- WHEN history injection is enabled
- THEN the `system` message and `_FEW_SHOT` entries appear unchanged, in their original positions, before any history entry

### Requirement: Token budget for injected history

History injection SHALL stay well within the model's context limit. For the default N=10 (20 messages worst case) and an approximate upper bound of 150 tokens per message, the injected history SHALL consume at most ~3000 tokens, keeping total input under ~4800 tokens — far below the Groq model's 128k limit (~4% usage). The persistence layer SHALL NOT truncate or summarise messages; truncation is by message count only (N), not by character length.

#### Scenario: Worst-case window fits comfortably

- GIVEN a student has 10 turns of messages each averaging 150 tokens
- WHEN the history window is injected
- THEN the total injected tokens are at most ~3000 and the assembled prompt is within the model limit
- AND no message content is truncated to fit a character budget

### Requirement: Database file location and writability

The SQLite file SHALL live at the path configured by `SQLITE_PATH` (default `./data/historial.db`) and SHALL be writable by the backend process. On platforms where the directory does not exist, the backend SHALL create it on startup. Persistence across HF Spaces sleep is NOT guaranteed (ephemeral disk) — this is an accepted trade-off (proposal decision 5) and SHALL be documented in AGENTS.md but NOT mitigated by this change.

#### Scenario: Directory is auto-created

- GIVEN `SQLITE_PATH=./data/historial.db` but `./data/` does not exist
- WHEN the backend boots
- THEN `./data/` is created and `historial.db` is initialised inside it

#### Scenario: Configure via env var

- GIVEN `SQLITE_PATH=/tmp/test_history.db`
- WHEN the backend boots
- THEN SQLite uses `/tmp/test_history.db` and not the default path
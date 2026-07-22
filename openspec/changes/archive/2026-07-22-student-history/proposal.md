# Proposal: Student History & Basic Identification

## Intent

The current system is fully anonymous and single-turn: each `POST /chat` request is independent, with no student identity, no conversation thread, and no persistence. The Socratic layer (previous change) explicitly deferred multi-turn behavior — "Conversation history / multi-turn scaffolding (separate SQLite cycle)" is listed as Out of Scope in `openspec/specs/socratic-guidance/spec.md:191`. This change is that separate cycle.

Student history transforms the prototype from a disposable Q&A tool into a persistent companion. Students return to the same conversation across sessions (within the same device/browser), see their previous exchanges, and can delete individual messages. The assistant gains conversational context — it can see what the student asked before — which is a prerequisite for true multi-turn Socratic scaffolding (though adapting the hint ladder based on history is explicitly out of scope for this change).

## Scope

### In Scope
- **Typed-name identification**: student types their display name before chatting; stored in `localStorage`; sent as `student_name` in each `POST /chat` request. No password, no email, no token.
- **Persistent conversation history in SQLite**: one continuous thread per identified student. All messages (user + assistant) persisted to `data/historial.db`.
- **Delete individual messages**: `DELETE /messages/{id}` endpoint. Student can remove any message from their own history. Conversation flow preserved (gaps are visible but not repaired).
- **Inject last 10 messages into Groq prompt**: when calling Groq, the last N messages (default N=10, configurable via env var `HISTORY_WINDOW`) are injected into the `messages` list between `_FEW_SHOT` and the current query.
- **Load history on page load**: frontend fetches the student's full history via `GET /history?student_name=...` and renders it in the chat UI.
- **Persist across HF Spaces sleep**: accepted trade-off — SQLite on ephemeral disk. History may be lost when the Space sleeps (~48h). Documented, not mitigated.

### Out of Scope
- Multi-conversation model (one thread per student — no "new conversation" button).
- Socratic hint adaptation based on history (decision 7 — separate future change).
- Password / email / token-based auth (decision 1).
- History persistence across HF Spaces sleep (decision 5 — no Storage Bucket, no remote DB).
- Pagination UI for large histories (start without; add later if needed).
- Dashboard integration (month 4 work).
- Changes to RAG retrieval logic, model, embeddings, or infrastructure.

## Capabilities

> This section is the CONTRACT between proposal and specs phases.
> The sdd-spec agent reads this to know exactly which spec files to create or update.

### New Capabilities
- `student-identification`: Typed-name identification flow — name input UI, `localStorage` persistence, `student_name` in request body, student lookup/creation in SQLite.
- `conversation-persistence`: SQLite schema (`students`, `messages` tables), message persistence lifecycle (persist user message before Groq, persist assistant message after stream), history retrieval endpoint, message deletion endpoint, history injection into Groq call.

### Modified Capabilities
- `socratic-guidance`: The Groq `messages` list now includes history between `_FEW_SHOT` and the current query. The Socratic system prompt is unchanged (no multi-turn adaptation), but the model receives conversation context it did not have before. The single-turn constraint is lifted at the infrastructure level (history is visible to the model), but the pedagogical behavior does not adapt to it yet.

## Approach

### Identification Flow
- **Where**: inline in the chat page. On first visit, the chat input is disabled and a name input is shown above it ("Enter your name to start"). After typing the name, the chat is enabled.
- **Client-side**: name stored in `localStorage`. Sent as `student_name` in every `POST /chat` request.
- **Server-side**: backend looks up or creates a `students` row by `display_name`. No unique constraint on name (name collisions merge histories — accepted trade-off for the prototype).
- **No logout**: to switch students, the student clears `localStorage` or uses a different browser/device.

### Persistence Model
Two SQLite tables:

```
students(id, display_name, created_at)
messages(id, student_id FK, role, content, created_at)
```

- `role` is `user` or `assistant`.
- No conversation table (one thread per student — decision 2).
- No password, no email, no session table.
- Schema initialized on first backend startup (auto-create if not exists).

### History Injection Strategy
In `rag/chain.py`, the `messages` list changes from:

```python
messages = [system] + _FEW_SHOT + [current_query]
```

To:

```python
messages = [system] + _FEW_SHOT + history + [current_query]
```

Where `history` is a list of `{"role": ..., "content": ...}` dicts fetched from SQLite (last N messages for the student, ordered by `created_at`). N defaults to 10, configurable via `HISTORY_WINDOW` env var.

Token budget: ~3000 tokens for 10 turns (20 messages × ~150 tokens/message). Total input ~4800 tokens — well within 128k limit (~4% usage).

### Edit Semantics
- `DELETE /messages/{id}` removes a single message from SQLite.
- The frontend re-renders the history after deletion.
- The assistant "sees" the gap: if a user message is deleted, the assistant's next response was based on that message, but the history no longer shows it. This is accepted — the model handles gaps gracefully (it sees a conversation with missing turns, which is a normal LLM scenario).
- Deleting an assistant message leaves the student's question visible but without a response. The student can re-ask.

### Cross-Cutting: Socratic Layer Wrap
Per the socratic-layer design, the system prompt uses the wrap approach (Socratic instructions prepended to RAG ground rules). This change does NOT modify the system prompt. History injection lives in the same `messages` list construction in `chain.py` — it is orthogonal to the prompt content.

The few-shot examples remain static and are injected before the history. The model sees: system → few-shot (pattern) → history (context) → current query.

### Persistence Lifecycle
- User message: persisted BEFORE calling Groq (safe even if Groq fails).
- Assistant message: persisted AFTER the stream completes (full response concatenated).
- If the stream fails mid-way: persist an error fallback message ("Ocurrió un error, intentá de nuevo").
- If the no-context fallback fires (cosine > 0.5): persist the user message + the hardcoded fallback phrase as the assistant message.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/main.py` | Modified | +`student_name` in `ChatRequest`. +`GET /history` endpoint. +`DELETE /messages/{id}` endpoint. |
| `app/static/chat.js` | Modified | +Name input UI. +`localStorage` for name. +Send `student_name` in request. +Load history on page load. +Delete button per message. |
| `app/static/index.html` | Modified | +Name input element (above chat input). |
| `app/static/style.css` | Modified | +Name input styling. +Delete button styling. |
| `rag/chain.py` | Modified | +`history` parameter in `generate_response`. +History injection into `messages` list. +Message persistence (user before Groq, assistant after stream). |
| `rag/history.py` | New | SQLite connection, schema init, CRUD operations for students and messages. |
| `data/historial.db` | New | SQLite database file (auto-created on first run). |
| `.env.example` | Modified | +`HISTORY_WINDOW` env var (default 10). `SQLITE_PATH` already declared. |

**NOT affected**: `rag/retrievers/*`, `rag/loaders/*`, `rag/splitters/*`, `rag/prompts/*`, `dashboard/*`, `Dockerfile`, deployment config.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| HF Spaces sleep loses all history | CRITICAL | Accepted trade-off (decision 5). Documented in AGENTS.md and proposal. If unacceptable in future, scope Storage Bucket or remote DB. |
| Name collisions merge histories | WARNING | Two "Juan Pérez" students share one thread. Mitigation: document the limitation. If it becomes a problem, add a disambiguation step (e.g., "Juan Pérez (2)"). |
| Breaking existing Socratic demo | WARNING | History injection is additive — the system prompt and few-shot are unchanged. Test the 8 demo queries + 10 Socratic queries to ensure no regression. |
| SQLite schema migration on deploy | WARNING | Auto-create on first run (`CREATE TABLE IF NOT EXISTS`). No migration tool needed for the prototype. If schema changes later, manual migration script. |
| Frontend complexity (name input, delete buttons, history rendering) | SUGGESTION | Keep the UI minimal: one name input, one delete button per message, no pagination. Total frontend diff: ~80 lines. |

## Rollback Plan

`git revert` of the commit(s) touching `app/main.py`, `app/static/*`, `rag/chain.py`, and `rag/history.py`. Delete `data/historial.db` if it exists. Remove `HISTORY_WINDOW` from `.env`. No model swap, no embedding re-bake, no deployment config change. Rollback is a single revert + DB file deletion.

## Dependencies

- Socratic layer (previous change) must be deployed. This change injects history into the same Groq call that the Socratic layer established.
- `data/` directory must be writable on HF Spaces (confirmed in `deploy-hf-spaces` explore).

## Success Criteria

- [ ] Student can type their name and start chatting (identification flow works).
- [ ] Student's name persists in `localStorage` across page reloads (same device/browser).
- [ ] All messages (user + assistant) are persisted in SQLite.
- [ ] Student can delete individual messages from their history.
- [ ] History is loaded and rendered on page load (full conversation visible).
- [ ] Groq receives the last 10 messages as context (verify via logging or debug endpoint).
- [ ] No regression on 8 demo queries from the Socratic layer.
- [ ] No regression on 10 Socratic behavior queries.
- [ ] HF Spaces sleep trade-off is documented in AGENTS.md.

## Open Questions

None — all 7 open questions from the exploration (OQ-1 through OQ-7) have been resolved in the product decisions round.

## References

- `openspec/changes/student-history/explore.md` — full exploration (722 lines).
- `openspec/changes/archive/2026-07-21-socratic-layer/proposal.md` — structural reference.
- `openspec/changes/archive/2026-07-21-socratic-layer/design.md` — wrap approach, few-shot injection, error handling pattern.
- `openspec/specs/socratic-guidance/spec.md:191` — "Conversation history / multi-turn scaffolding" listed as Out of Scope. This change fulfills that deferred cycle.
- `AGENTS.md` §3 (non-negotiable: "History per student"), §7 decision 8 (cold-start trade-off), §9 (permissions: "Student can edit own history"), §13 (open questions: auth strategy, history retention).

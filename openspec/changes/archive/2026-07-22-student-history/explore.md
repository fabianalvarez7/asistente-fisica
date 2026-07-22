# Exploration: Student History & Basic Identification

> **Status**: complete
> **Change**: `student-history`
> **Scope**: SQLite conversation history + lightweight student identification. No dashboard, no advanced auth, no multi-device sync.

---

## Executive Summary

The current system is **fully anonymous and single-turn**: each `POST /chat` request is independent — no student identity, no conversation thread, no persistence. The `data/historial.db` path is declared in `.env.example` (line 15) but **no SQLite code exists anywhere in the codebase**. The frontend (`app/static/chat.js`) maintains no client-side state either. Adding student history requires two tightly coupled capabilities: (1) a way to identify the student (even minimally), and (2) a persistence layer for the conversation thread. The main design tensions are: (a) how much identification is "enough" for a prototype serving a public university (spoofable name vs. real auth), (b) how to thread multi-turn context into the Groq call without blowing up the 128k context window, and (c) what "student can edit own history" (AGENTS.md §9) means in practice for the prototype.

---

## 1. Current State (Code Audit)

### 1.1 Chat Endpoint — `app/main.py:43-60`

```python
class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Pregunta del estudiante de Física 1",
    )

@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        generate_response(req.query),
        media_type="text/event-stream",
    )
```

**Key observations:**
- The request body contains ONLY `query`. No student ID, no session ID, no conversation ID.
- The endpoint is stateless. It calls `generate_response(req.query)` with a single string and streams back SSE frames.
- No middleware for auth, cookies, or session tracking.
- No database connection, no SQLite import, no history read/write.

### 1.2 RAG Chain — `rag/chain.py:93-151`

```python
def generate_response(query: str) -> Generator[str, None, None]:
    # ...
    stream = _OPENAI_CLIENT.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            *_FEW_SHOT,
            {"role": "user", "content": query},
        ],
        stream=True,
        temperature=0.0,
    )
```

**Key observations:**
- `generate_response` takes a single `query: str`. It has no concept of conversation history.
- The `messages` list is: system + 6 few-shot messages (3 user/assistant pairs) + 1 user message. Total: 8 messages.
- There is no mechanism to inject previous turns into the Groq call.
- The function is a pure generator: query in → tokens out. No side effects, no persistence.
- The few-shot examples are hardcoded in `_FEW_SHOT` (lines 35-81). They are NOT conversation history — they are static pedagogical examples.

### 1.3 Frontend — `app/static/chat.js`

- Sends `POST /chat` with `{ query: string }` (line 124-128).
- Receives SSE stream, appends tokens to a chat bubble.
- **No conversation history is maintained client-side.** Each request is independent.
- No `localStorage`, no `sessionStorage`, no cookies, no URL params.
- No login screen, no name input, no identification of any kind.
- The page has no concept of "session" or "conversation" — it's a single message in, single response out.

### 1.4 Frontend HTML — `app/static/index.html`

- 41 lines. Contains: header, message list, input form, hint area.
- **No identification UI**: no name field, no login modal, no session indicator.
- No "new conversation" button, no history sidebar, no student profile.
- The page is completely anonymous.

### 1.5 SQLite — Declared but Not Implemented

| Location | What exists | What's missing |
|----------|-------------|----------------|
| `.env.example:14-15` | `SQLITE_PATH=./data/historial.db` | No code reads this env var |
| `AGENTS.md:71-73` | `data/historial.db` in repo structure | File does not exist on disk |
| `AGENTS.md:208` | `SQLITE_PATH` env var documented | No code uses it |
| `data/` directory | Contains `chroma/` and `pdfs/` only | No `historial.db` file |
| `requirements.txt` | No `sqlite3` entry (it's in Python stdlib) | N/A |

**Verified**: `grep -r "sqlite\|historial\|SQLite" --include="*.py"` returns ZERO hits in any Python file. The entire persistence layer is unimplemented.

### 1.6 Deploy Context — HF Spaces (not Render)

Per the archived `deploy-hf-spaces` change, the deploy target is now HF Spaces Docker (free cpu-basic: 16 GB RAM, ~48 h sleep). Key implications for history:

- The HF Space ephemeral disk is **writable during runtime** (confirmed in `openspec/changes/deploy-hf-spaces/explore.md:121`).
- SQLite writes to the ephemeral disk will work at runtime.
- **BUT**: ephemeral disk is lost on sleep/restart. History stored only in SQLite will be lost when the Space sleeps (~48 h inactivity).
- The pre-baked artifacts (`rag/index/chroma/`, `rag/index/hf-model/`) survive sleep because they're in git. History cannot use this strategy — it's write-once-at-runtime data.
- This is a known trade-off for the prototype: "We accept the cold-start trade-off for the prototype" (AGENTS.md §7 decision 8). History loss on sleep is a similar acceptable trade-off, but it must be documented.

### 1.7 Socratic Layer Interaction

The archived `socratic-layer` change established:
- System prompt with Socratic instructions (`rag/prompts/chat_prompt.py`, 40 lines).
- 3 few-shot examples injected as messages in the Groq call (`rag/chain.py:35-81`).
- **Single-turn constraint explicitly accepted**: "SQLite history is a separate cycle. The model asks guiding questions but cannot track previous answers" (`openspec/changes/archive/2026-07-21-socratic-layer/design.md:14`).
- The socratic-guidance spec explicitly lists "Conversation history / multi-turn scaffolding (separate SQLite cycle)" as **Out of Scope** (`openspec/specs/socratic-guidance/spec.md:191`).

**This change is that separate cycle.** The Socratic layer's architecture already anticipated it.

---

## 2. Design Space: Student Identification

### 2.1 What Is a "Student"?

The AGENTS.md §9 permissions table says:

| Role | Can chat | Can upload content | Can view dashboard | Can edit own history |
|------|----------|-------------------|-------------------|---------------------|
| Student | Yes | No | No | Yes (own history) |

But it does not define what a "student" is. The open questions in AGENTS.md §13 list:
- "Authentication strategy — simple user/pass in SQLite? Magic link? Depends on faculty IT. Month 3 work."
- "Minimum viable identification may be enough."

The identification strategy determines the entire history architecture. Here are the viable options:

### 2.2 Option A: Typed Name Only (No Auth)

The student types their name (e.g., "Juan Pérez") into a text field before chatting. The name is stored in `localStorage` and sent with each request.

**Schema**:
```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- No password, no email, no unique constraint on name
```

**How it works**:
1. First visit: frontend shows a name input. Student types "Juan Pérez".
2. Frontend stores the name in `localStorage` and sends it as `student_name` in the `POST /chat` body.
3. Backend looks up or creates a `students` row by `display_name`.
4. Messages are associated with the student's `id`.

**Pros**:
- Trivially simple. ~50 lines of backend, ~30 lines of frontend.
- No password management, no email verification, no IT dependency.
- Works for the prototype's scale (one class, ~50-100 students).
- Student can "edit own history" by simply deleting messages (the backend exposes a `DELETE /messages/{id}` endpoint).

**Cons**:
- Trivially spoofable: any student can type anyone else's name.
- No privacy: if two students share a device, they see each other's history.
- Name collisions: two "Juan Pérez" students merge into one history.
- No real "ownership" — the student's identity is just a string.

**Effort**: Low (2-3 days).

### 2.3 Option B: Username + Password (SQLite Auth)

The student registers with a username + password. Password is hashed (bcrypt/argon2) and stored in SQLite. Login via `POST /login` → returns a session token (cookie or JWT).

**Schema**:
```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**How it works**:
1. First visit: frontend shows a registration form (username + password + display name).
2. Subsequent visits: login form. Backend validates credentials, returns a session token.
3. Token is stored in `localStorage` (or an `httpOnly` cookie) and sent with each request.
4. Backend validates the token on each request and associates messages with the student.

**Pros**:
- Real authentication. Students own their history.
- No name collisions (username is unique).
- Privacy: each student sees only their own history.
- "Edit own history" is meaningful — only the owner can delete their messages.

**Cons**:
- More work: ~150 lines of backend (registration, login, session management, password hashing), ~80 lines of frontend (registration form, login form, token handling).
- Password management: students forget passwords. No email recovery (no SMTP). Password reset is a manual process (Fabián edits the DB).
- Requires `bcrypt` or `argon2` dependency.
- Overkill for a prototype serving 50-100 students in one class.

**Effort**: Medium (5-7 days).

### 2.4 Option C: Magic Link via Email

The student enters their email. Backend sends a login link. Student clicks the link → authenticated.

**Why this is NOT viable**:
- Requires SMTP (email sending). The project has no email service.
- HF Spaces free tier has outbound network restrictions (ports 80, 443, 8080 only — SMTP uses 587/465).
- Faculty IT is not involved. No university email integration.
- Overkill for a prototype.

**Effort**: High (not viable).

### 2.5 Option D: Shareable URL with Token

The student gets a unique URL (e.g., `https://app.example.com/chat?token=abc123`). The token is generated once (by Fabián or Nair) and given to the student. The token is stored in `localStorage` and sent with each request.

**Schema**:
```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT,
    access_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**How it works**:
1. Fabián generates tokens (e.g., `python scripts/generate_tokens.py --count 50`).
2. Tokens are distributed to students (via Nair, email, QR code in class).
3. Student visits the URL with the token. Frontend stores it in `localStorage`.
4. Backend validates the token on each request.

**Pros**:
- No password management.
- Tokens are unique — no collisions.
- Simple to generate and distribute.
- "Edit own history" is meaningful — only the token holder can access the history.

**Cons**:
- Token distribution is a manual process (Fabián/Nair must hand out tokens).
- If a student loses their token, they lose access to their history (no recovery).
- Tokens are shareable — a student can give their URL to a friend.
- No self-service registration.

**Effort**: Low-Medium (3-4 days).

### 2.6 Option E: Browser-Only (localStorage, No Backend Identity)

The student is identified by a UUID stored in `localStorage`. No backend identity. History is associated with the UUID.

**Schema**:
```sql
CREATE TABLE students (
    id TEXT PRIMARY KEY,  -- UUID from localStorage
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Why this violates AGENTS.md**:
- AGENTS.md §3 says: "Conversations are not anonymous." A `localStorage` UUID is anonymous — if the student clears their browser, the history is orphaned.
- AGENTS.md §9 says: "Student can edit own history." With a `localStorage` UUID, the student can only edit history on the device where the UUID was generated. If they switch devices, they lose access.

**Effort**: Low (but violates non-negotiable constraints).

### 2.7 Decision Matrix

| Criterion | A (Name) | B (User+Pass) | C (Magic Link) | D (Token URL) | E (localStorage) |
|-----------|----------|---------------|----------------|---------------|------------------|
| Violates "not anonymous" | Risky | ✅ No | ✅ No | ✅ No | **YES** |
| Spoofable | **YES** | ✅ No | ✅ No | Shareable | **YES** |
| Password recovery | N/A | Manual (no SMTP) | Email | Lost = orphaned | N/A |
| IT dependency | None | None | **High** | None | None |
| Dev effort | Low | Medium | High (not viable) | Low-Medium | Low |
| Fits prototype scale | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ❌ No |
| "Edit own history" | Weak | ✅ Strong | ✅ Strong | ✅ Strong | ❌ Device-only |

**Recommendation**: The exploration does NOT pick a winner. The proposal phase should evaluate Options A, B, and D against the prototype's constraints. Option C is not viable (no SMTP). Option E violates non-negotiable constraints.

---

## 3. Design Space: Conversation History Schema

### 3.1 What Is a "Conversation"?

Two models:

**Model A: One continuous thread per student.**
- Each student has exactly one conversation. All messages go into the same thread.
- Simple schema: `messages(student_id, role, content, timestamp)`.
- Pros: trivial to implement, no concept of "new conversation."
- Cons: the thread grows forever. After 50 messages, the context window is polluted with old, irrelevant turns. The student cannot "start over" on a new exercise.

**Model B: Multiple conversations per student.**
- Each student can have multiple conversations (threads). Each conversation has a title or topic.
- Schema: `conversations(id, student_id, title, created_at)`, `messages(id, conversation_id, role, content, timestamp)`.
- Pros: the student can start a new conversation for each exercise. The context window stays focused.
- Cons: more complex schema, UI needs a "new conversation" button and a conversation list.

**Recommendation**: The exploration does NOT pick a winner. The proposal phase should evaluate both models. Model A is simpler but may not serve the pedagogical use case well (students work on multiple exercises). Model B is more flexible but adds UI complexity.

### 3.2 Schema Sketch (Model B — Multiple Conversations)

```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- identification fields depend on Option A/B/D above
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    title TEXT,  -- optional, could be auto-generated from first message
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_conversations_student ON conversations(student_id, created_at);
```

### 3.3 What to Persist

Each message in the conversation is persisted verbatim:
- **User message**: the student's query (max 500 chars, already validated by `ChatRequest`).
- **Assistant message**: the full SSE response (all tokens concatenated).

**Question**: should the retrieved context (the 4 chunks from ChromaDB) also be persisted?

**Option A: Persist only user + assistant messages.**
- Pros: simple, small storage.
- Cons: if the student re-reads the conversation later, they don't see what context the assistant used. Debugging retrieval quality is harder.

**Option B: Persist user + assistant + context.**
- Pros: full audit trail. Debugging retrieval quality is easier.
- Cons: larger storage. The context is ~800-1200 tokens per message — significant.

**Recommendation**: Option A for the prototype. The context is not part of the "conversation" from the student's perspective. If debugging retrieval quality is needed, the dashboard (month 4) can log it separately.

### 3.4 How Long Is History Retained?

**Option A: Forever (no deletion).**
- Pros: simple.
- Cons: the database grows. After a semester, a student may have 500+ messages. Loading the full history into the Groq context window is impossible (128k tokens, but each message is ~100-300 tokens → 500 messages = 50k-150k tokens).

**Option B: Last N messages (sliding window).**
- Pros: the Groq context window stays manageable.
- Cons: the student loses access to older messages in the UI.

**Option C: All messages persisted, but only last N injected into Groq.**
- Pros: the student sees the full history in the UI. The Groq call gets only the most relevant recent turns.
- Cons: more complex query logic.

**Recommendation**: Option C. Persist everything, but inject only the last K messages (e.g., K=10) into the Groq call. The UI shows the full history (with pagination if needed). This separates "what the student sees" from "what the model sees."

### 3.5 How to Inject History into the Groq Call

The current `generate_response` in `rag/chain.py:93-151` builds the `messages` list as:

```python
messages = [
    {"role": "system", "content": prompt},
    *_FEW_SHOT,  # 6 messages (3 user/assistant pairs)
    {"role": "user", "content": query},
]
```

To add history, the `messages` list becomes:

```python
messages = [
    {"role": "system", "content": prompt},
    *_FEW_SHOT,  # 6 messages (static few-shot examples)
    *history,    # N messages from SQLite (last K turns)
    {"role": "user", "content": query},
]
```

**Question**: where should `history` go — before or after `_FEW_SHOT`?

**Option A: After few-shot, before the current query.**
```python
messages = [system] + _FEW_SHOT + history + [current_query]
```
- Pros: the few-shot examples set the pedagogical pattern, then the history provides context, then the current query. The model sees the pattern first, then the specific conversation.
- Cons: if the history is long, the few-shot examples may be "forgotten" by the model (attention dilution).

**Option B: Before few-shot, after system.**
```python
messages = [system] + history + _FEW_SHOT + [current_query]
```
- Pros: the history is closest to the system prompt (which the model pays attention to). The few-shot examples are fresh in the model's attention.
- Cons: the history may interfere with the few-shot pattern.

**Recommendation**: Option A (after few-shot, before current query). This is the standard pattern for multi-turn LLM conversations: system → few-shot → history → current query. The few-shot examples establish the pedagogical pattern; the history provides the specific conversation context.

**Token budget analysis**:
- System prompt: ~450-600 tokens (from socratic-layer design).
- Few-shot (3 pairs): ~300-400 tokens.
- History (10 turns × 2 messages/turn × ~150 tokens/message): ~3000 tokens.
- Current query: ~50-100 tokens.
- **Total input**: ~3800-4100 tokens. Well within 128k limit (~3% usage).

Even with 20 turns of history, the total is ~7000 tokens (~5% of 128k). Token budget is NOT a constraint.

### 3.6 When to Persist

**Option A: Persist the user message BEFORE calling Groq, then persist the assistant message AFTER the stream completes.**
- Pros: the user message is safe even if Groq fails.
- Cons: if the stream fails mid-way, the assistant message is incomplete or missing. The conversation has a user message with no response.

**Option B: Persist both messages AFTER the stream completes.**
- Pros: the conversation is always complete (user + assistant).
- Cons: if the backend crashes mid-stream, both messages are lost.

**Option C: Persist the user message before Groq, then stream the assistant response, then persist the assistant message. If the stream fails, persist a fallback message ("Ocurrió un error, intentá de nuevo").**
- Pros: the user message is safe. The assistant message is always present (even if it's an error).
- Cons: more complex logic.

**Recommendation**: Option C. It matches the existing error-handling pattern in `rag/chain.py:148-151` (the generator catches exceptions and yields an error frame, then `[DONE]`). The persistence layer should mirror this: persist the user message, stream the response, persist the assistant message (or an error fallback).

---

## 4. Design Space: UX Shape

### 4.1 Where Does Identification Happen?

**Option A: Before the first message (dedicated screen).**
- First visit: the student sees a login/registration screen. After identification, they see the chat.
- Pros: clear separation of concerns. The chat is only for chatting.
- Cons: adds a step before the student can chat. If the student just wants to ask a quick question, they must log in first.

**Option B: Inline in the chat (modal or banner).**
- First visit: the student sees the chat, but the input is disabled. A banner says "Enter your name to start." The student types their name, and the chat is enabled.
- Pros: the student sees the chat immediately. The identification is minimal friction.
- Cons: the identification is "in the way" of the chat. If the student wants to switch accounts, they must clear `localStorage` or log out.

**Option C: In the URL (token-based, Option D from §2).**
- The student visits a URL with a token (e.g., `https://app.example.com/chat?token=abc123`). The token is stored in `localStorage` and the chat is enabled.
- Pros: zero friction. The student just clicks the link.
- Cons: the token must be distributed externally (email, QR code, etc.).

**Recommendation**: The exploration does NOT pick a winner. The proposal phase should evaluate all three. Option A is clearest. Option B is lowest friction. Option C is zero friction but requires external token distribution.

### 4.2 Does the Student See Their History?

**Option A: Yes, all of it (with pagination).**
- The chat UI shows the full conversation history. If the conversation has 100+ messages, the UI paginates (load more on scroll).
- Pros: the student can review their entire conversation.
- Cons: the UI must handle pagination. The initial load may be slow if the conversation is long.

**Option B: Yes, but only the last N messages.**
- The chat UI shows the last 20 messages. Older messages are not visible.
- Pros: simple UI. Fast initial load.
- Cons: the student loses access to older messages.

**Option C: Yes, all of it, organized by conversation (Model B from §3.1).**
- The chat UI shows a list of conversations (sidebar or dropdown). The student selects a conversation and sees its messages.
- Pros: the student can organize their work by exercise/topic.
- Cons: more complex UI. Requires a "new conversation" button, a conversation list, and a message list.

**Recommendation**: The exploration does NOT pick a winner. The proposal phase should evaluate all three. Option A is simplest. Option B is fastest. Option C is most flexible but adds UI complexity.

### 4.3 What Does "Edit Own History" Mean?

AGENTS.md §9 says: "Student can edit own history." This is ambiguous. Three interpretations:

**Interpretation A: Delete individual messages.**
- The student can delete a specific message (user or assistant) from the conversation.
- Pros: the student can remove mistakes or irrelevant messages.
- Cons: deleting a user message breaks the conversation flow (the assistant's response was based on that message). Deleting an assistant message is confusing (the student sees a gap).

**Interpretation B: Delete the entire conversation.**
- The student can delete the entire conversation (all messages).
- Pros: the student can "start over" if the conversation is derailed.
- Cons: destructive. The student may accidentally delete a valuable conversation.

**Interpretation C: Clear the conversation (soft delete).**
- The student can "clear" the conversation (mark it as archived). The messages are still in the database but not visible in the UI.
- Pros: non-destructive. The student can "un-archive" the conversation later.
- Cons: more complex schema (needs an `archived` flag).

**Recommendation**: The exploration does NOT pick a winner. The proposal phase should clarify with Fabián/Nair what "edit own history" means. Interpretation B (delete entire conversation) is simplest and most likely what was intended. Interpretation A (delete individual messages) is complex and breaks conversation flow. Interpretation C (soft delete) is a nice-to-have.

---

## 5. Affected Areas

| File | Why it's affected |
|------|-------------------|
| `app/main.py` | Must accept student identity in the request body. Must add endpoints for history retrieval, conversation management, and (optionally) registration/login. |
| `app/static/chat.js` | Must send student identity with each request. Must load and display history on page load. Must handle conversation switching (if Model B). |
| `app/static/index.html` | Must add identification UI (login/registration form or name input). Must add history UI (conversation list, pagination). |
| `app/static/style.css` | Must style the new UI elements (identification form, conversation list, pagination). |
| `rag/chain.py` | `generate_response` must accept a `history` parameter (list of previous messages) and inject it into the Groq `messages` list. |
| `data/historial.db` | Must be created. Schema must be defined. Migrations must be handled. |
| `requirements.txt` | May need `bcrypt` or `argon2` if Option B (username + password) is chosen. |
| `.env.example` | `SQLITE_PATH` is already declared. May need additional env vars (e.g., `SESSION_SECRET` if using cookies). |
| `scripts/` | May need a script to generate tokens (if Option D) or to initialize the database schema. |

**NOT affected**: `rag/retrievers/*`, `rag/loaders/*`, `rag/splitters/*`, `rag/prompts/*`, `dashboard/*`, `Dockerfile`, `render.yaml`.

---

## 6. Edge Cases

### 6.1 Student Closes Browser, Comes Back Tomorrow

**Depends on identification choice**:
- Option A (name): the name is in `localStorage`. The student sees their history. ✅
- Option B (username + password): the session token may have expired. The student must log in again. ✅
- Option D (token URL): the token is in `localStorage`. The student sees their history. ✅
- **HF Spaces sleep**: if the Space has slept (~48 h), the SQLite database on the ephemeral disk is LOST. The student sees an empty history. ❌

**Mitigation for HF Spaces sleep**: this is a known trade-off for the prototype. The history is lost when the Space sleeps. If this is unacceptable, the SQLite database must be persisted to a Storage Bucket (HF Spaces feature) or a remote database (Postgres). Both are out of scope for the prototype.

### 6.2 Two Students Share a Device

**Depends on identification choice**:
- Option A (name): the name is in `localStorage`. The second student sees the first student's history. ❌
- Option B (username + password): the second student must log in with their own credentials. They see only their own history. ✅
- Option D (token URL): the token is in `localStorage`. The second student sees the first student's history. ❌

**Mitigation**: Option B is the only one that handles shared devices correctly. Options A and D require the students to clear `localStorage` or use a different browser/device.

### 6.3 Student's History Grows Large

**Depends on retention choice**:
- Option A (persist all, inject last K): the UI must paginate. The Groq call is unaffected (only last K messages are injected). ✅
- Option B (persist last N only): the UI is simple. Older messages are lost. ✅

**Mitigation**: Option A is recommended. Pagination is a standard UI pattern. The Groq call is unaffected.

### 6.4 Render / HF Spaces Cold Start with In-Flight History

**What happens**: the student sends a message. The backend starts streaming the response. The Space goes to sleep (or crashes). The student loses the response.

**Mitigation**: this is a known trade-off for the prototype. The student can refresh the page and try again. The user message is persisted (if Option C from §3.6), so the conversation is not lost — only the assistant's response is missing.

### 6.5 Student Sends a Message While the Backend Is Streaming

**What happens**: the frontend disables the input while streaming (`setLoading(true)` in `chat.js:51-54`). The student cannot send another message until the stream completes. ✅

**No change needed**: the existing frontend already handles this.

### 6.6 Student Sends a Message That Triggers the No-Context Fallback

**What happens**: the cosine distance > 0.5. The chain short-circuits with "No encuentro info sobre esto en los apuntes" (`rag/chain.py:119-122`). The assistant message is the fallback phrase.

**Should this be persisted?** Yes. The student asked a question, and the assistant responded (even if it's a refusal). The conversation should show the full exchange.

---

## 7. Cross-References to Socratic Layer

The socratic-layer change (`openspec/changes/archive/2026-07-21-socratic-layer/`) has several touchpoints with this change:

### 7.1 Single-Turn Constraint Is Lifted

The socratic-guidance spec explicitly lists "Conversation history / multi-turn scaffolding (separate SQLite cycle)" as **Out of Scope** (`openspec/specs/socratic-guidance/spec.md:191`). This change is that separate cycle. After this change, the Socratic layer can do true multi-turn scaffolding: the model can see the full conversation and adapt its hint level based on the student's previous answers.

**Implication**: the socratic-guidance spec's "Single-turn behaviour is enforced" requirement (`openspec/specs/socratic-guidance/spec.md:129-143`) must be updated or superseded. The new spec should define multi-turn behavior.

### 7.2 Few-Shot Examples Remain Static

The few-shot examples in `rag/chain.py:35-81` are static pedagogical examples. They are NOT conversation history. They should remain in the Groq call, injected before the history.

**No change needed**: the few-shot examples are orthogonal to the history.

### 7.3 System Prompt May Need Updates

The system prompt (`rag/prompts/chat_prompt.py`) currently says:
- "Sos un asistente de Física 1. Tu rol es guiar al estudiante con preguntas para que piense y resuelva solo."

With history, the model can see the student's previous answers. The system prompt may need to instruct the model to:
- Track the student's progress through the hint ladder.
- Avoid repeating the same guiding question.
- Adapt the hint level based on the student's previous answers.

**Implication**: the system prompt may need a "multi-turn Socratic" section. This is a follow-up change, not part of this exploration.

### 7.4 Error Handling Must Be Consistent

The socratic-layer change established a specific error-handling pattern:
- Cosine distance > 0.5 → hardcoded fallback, Groq never called.
- Context present but irrelevant → prompt instructs model to refuse.
- Exception → error frame, then `[DONE]`.

The history persistence must mirror this pattern:
- If the fallback fires, persist the user message + the fallback phrase as the assistant message.
- If an exception occurs, persist the user message + an error fallback as the assistant message.

**No change needed**: the existing error-handling pattern is compatible with history persistence.

---

## 8. Open Product Questions

These are decisions only the human (Fabián, with Nair's input) can make. The proposal phase cannot proceed without answers.

### OQ-1: Identification Strategy

Which identification strategy (A: typed name, B: username + password, D: token URL) should the prototype use?

**Context**: Option A is simplest but spoofable. Option B is real auth but overkill for a prototype. Option D is in-between but requires manual token distribution. AGENTS.md §13 says "Minimum viable identification may be enough" — but what is "minimum viable"?

**Recommendation**: Fabián should discuss with Nair. If the class is small (~50 students) and the prototype is short-lived (4 months), Option A (typed name) may be enough. If the prototype will be used by multiple classes or semesters, Option B (username + password) is more sustainable.

### OQ-2: Conversation Model

Should the prototype support one continuous thread per student (Model A) or multiple conversations per student (Model B)?

**Context**: Model A is simpler. Model B is more flexible (students can organize by exercise/topic). AGENTS.md §9 says "Student can edit own history" — this is easier with Model B (delete a conversation) than Model A (delete individual messages).

**Recommendation**: Fabián should discuss with Nair. If students typically work on one exercise at a time, Model A is enough. If students work on multiple exercises in parallel, Model B is better.

### OQ-3: "Edit Own History" Definition

What does "edit own history" mean in practice?

- Delete individual messages? (Breaks conversation flow)
- Delete the entire conversation? (Destructive)
- Clear/archive the conversation? (Non-destructive, more complex)

**Recommendation**: Fabián should clarify with Nair. The simplest interpretation is "delete the entire conversation." If Nair wants more granular control, the proposal should scope it.

### OQ-4: History Retention

How long should history be retained?

- Forever (no deletion)?
- Last N messages (sliding window)?
- All messages persisted, but only last N injected into Groq?

**Recommendation**: Option C (persist all, inject last N) is the most flexible. The UI can show the full history (with pagination), and the Groq call stays manageable.

### OQ-5: HF Spaces Sleep and History Loss

The HF Space ephemeral disk is lost on sleep (~48 h inactivity). Should the prototype accept this trade-off, or should history be persisted to a Storage Bucket (HF Spaces feature)?

**Context**: AGENTS.md §7 decision 8 says "We accept the cold-start trade-off for the prototype." History loss on sleep is a similar trade-off. But if Nair expects students to have persistent history across sessions, this is a problem.

**Recommendation**: Fabián should clarify with Nair. If history loss on sleep is acceptable, the prototype can use SQLite on the ephemeral disk. If not, the proposal should scope a Storage Bucket or remote database.

### OQ-6: Nair's Checkpoint Cadence

Does Nair need to weigh in on the identification flow, or is this purely a dev call?

**Context**: AGENTS.md §8 says weeks 5-6 end with "Behaviour is the pedagogical differentiator" demo. Student history is operational, not pedagogical. But the identification flow affects the student experience, which Nair may care about.

**Recommendation**: Fabián should show Nair the identification options (A, B, D) and get her input. If Nair has no preference, the dev team can pick the simplest option.

### OQ-7: Multi-Turn Socratic Behavior

After history is implemented, should the Socratic layer adapt its hint level based on the student's previous answers?

**Context**: The socratic-layer change established a single-turn constraint. With history, the model can see the student's previous answers and adapt. But this requires updating the system prompt and testing the behavior.

**Recommendation**: This is a follow-up change, not part of this exploration. The proposal should scope it as a separate change or as part of this change.

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **HF Spaces sleep loses history** | CRITICAL | Document the trade-off. If unacceptable, scope a Storage Bucket or remote database. |
| **Identification strategy is too weak (Option A)** | WARNING | Fabián should discuss with Nair. If spoofing is a concern, pick Option B or D. |
| **Conversation model is too simple (Model A)** | WARNING | Fabián should discuss with Nair. If students need multiple conversations, pick Model B. |
| **History injection blows up the Groq context window** | SUGGESTION | Unlikely at K=10 turns (~3000 tokens). Even K=20 is ~7000 tokens (~5% of 128k). Monitor if future iterations push past K=50. |
| **Breaking the existing demo** | WARNING | The wrap approach preserves all existing grounding rules. Test the exact same queries from the last demo to ensure they still work. |
| **SQLite schema migration** | WARNING | Use a migration tool (e.g., `alembic`) or manual migrations. For the prototype, manual migrations are enough. |
| **Frontend complexity (conversation list, pagination)** | WARNING | Start with Model A (one thread) and no pagination. Add Model B and pagination in a follow-up if needed. |
| **"Edit own history" is ambiguous** | WARNING | Fabián should clarify with Nair. Default to "delete entire conversation" if no preference. |
| **Cross-platform dev (macOS + Windows)** | SUGGESTION | SQLite is cross-platform. No issues expected. Test on both platforms before deploying. |
| **Password management (Option B)** | WARNING | If Option B is chosen, students will forget passwords. No email recovery (no SMTP). Fabián must manually reset passwords. |

---

## 10. Recommendation Summary

The exploration does NOT pick a winner. The proposal phase should evaluate the options against the prototype's constraints and Fabián/Nair's preferences.

**Key decisions to make before the proposal**:
1. Identification strategy (A, B, or D).
2. Conversation model (A or B).
3. "Edit own history" definition.
4. History retention policy.
5. HF Spaces sleep trade-off (accept or mitigate).
6. Nair's input on the identification flow.

**What the proposal should deliver**:
- A concrete identification strategy with schema.
- A concrete conversation model with schema.
- A concrete history persistence layer (SQLite).
- A concrete UX flow (identification UI, history UI).
- A concrete plan for injecting history into the Groq call.
- A concrete plan for handling edge cases (HF Spaces sleep, shared devices, large history).
- A concrete rollback plan.

---

## Ready for Proposal

**Conditional.** The exploration has enough technical detail to feed the proposal phase, but the product questions (OQ-1 through OQ-7) must be resolved first. The orchestrator should tell the user:

> "The student-history change requires two tightly coupled capabilities: student identification and conversation persistence. The current system is fully anonymous and single-turn — no SQLite code exists, no identification UI exists. The design space is well-mapped: 3 viable identification strategies (typed name, username + password, token URL), 2 conversation models (one thread vs. multiple threads), and several edge cases (HF Spaces sleep loses history, shared devices, large history). Before the proposal can proceed, Fabián must answer 7 product questions (OQ-1 through OQ-7) — the most critical being: which identification strategy should the prototype use, and does Nair need to weigh in on the identification flow?"

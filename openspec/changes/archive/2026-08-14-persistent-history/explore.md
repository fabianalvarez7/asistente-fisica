# Exploration: Persistent History Across HF Spaces Sleep

> **Status**: complete
> **Change**: `2026-08-14-persistent-history`
> **Scope**: Fix the loss of conversation history when the HF Space sleeps (~48h inactivity → ephemeral disk wipe). Two proposed fixes: (A) frontend `localStorage` for identity, (B) backend migration to Turso. Keep typed-name identification; do NOT replace it with "cursada conditions."

---

## Executive Summary

The conversation history persistence layer is **fully implemented and working** — typed-name identification, SQLite schema, message persistence lifecycle, history injection into Groq, and delete endpoints are all shipped and documented in `openspec/specs/conversation-persistence/spec.md` and `openspec/specs/student-identification/spec.md`. The **only gap** is that SQLite lives on HF Spaces' ephemeral disk, so history is lost when the Space sleeps after ~48h of inactivity. AGENTS.md §7 decisions #11 and #12 explicitly accept this trade-off for the prototype, but the team now wants to fix it. Two fixes are proposed: (A) ensure the frontend remembers the student's display name across browser sessions (already implemented — `localStorage` is in use), and (B) migrate the conversation DB from SQLite-on-ephemeral-disk to Turso (libSQL, SQLite-compatible, free tier 9 GB, no sleep). This exploration confirms that Fix A is already done, Fix B is the real solution, and Turso is the right pick over Supabase/Neon for the prototype's constraints.

---

## 1. Current State (Code Audit)

### 1.1 What's Already Shipped

The student-history change (archived 2026-07-22) delivered a complete persistence layer. Every component documented in the proposal and specs is present in the codebase:

| Component | Status | Location | Evidence |
|-----------|--------|----------|----------|
| Typed-name identification | ✅ Shipped | `app/static/chat.js:28,230`, `app/static/index.html:20-30` | `localStorage.getItem('student_name')` on load; name input gates the chat |
| `student_name` in request body | ✅ Shipped | `app/main.py:85-89`, `app/static/chat.js:172` | `ChatRequest` requires `student_name`; frontend sends it in `POST /chat` |
| SQLite schema (students, messages) | ✅ Shipped | `rag/history.py:52-92` | `init_db()` creates tables with `CREATE TABLE IF NOT EXISTS` |
| Message persistence lifecycle | ✅ Shipped | `app/main.py:105,119,133,143` | User message saved before Groq; assistant message saved after stream; error fallback persisted |
| History injection into Groq | ✅ Shipped | `rag/chain.py:93-145`, `app/main.py:106` | `generate_response(query, history=history)` injects last N messages between `_FEW_SHOT` and current query |
| `GET /history` endpoint | ✅ Shipped | `app/main.py:153-165` | Returns all messages for a student, ordered by `created_at` ASC |
| `DELETE /messages/{id}` endpoint | ✅ Shipped | `app/main.py:168-184` | Verifies ownership via `student_name`; returns 403/404 appropriately |
| `HISTORY_WINDOW` env var | ✅ Shipped | `app/main.py:59-61`, `.env.example:28` | Default 10; configurable |
| Frontend loads history on page load | ✅ Shipped | `app/static/chat.js:246-261,303-306` | `loadHistory()` fetches and renders messages; called on load if `studentName` is present |
| Per-message delete buttons | ✅ Shipped | `app/static/chat.js:74-84,270-283` | Delete button per message; click handler calls `DELETE /messages/{id}` |

**Conclusion**: The persistence layer is complete. The only missing piece is **cross-sleep durability** — the SQLite file is lost when HF Spaces wipes the ephemeral disk.

### 1.2 The Gap: Ephemeral Disk

AGENTS.md §7 decision #12 explicitly documents this:

> "HF Spaces via Docker SDK. The deploy is described by a `Dockerfile` plus a Space `README.md` with `sdk: docker` and `app_port: 7860`. The container runs as UID 1000, the embedding model is tracked via Git LFS, and pre-baked artifacts survive sleep/wake."

And decision #11:

> "Typed-name identification for the chat, not user/password auth. The prototype asks the student for a display name and uses it as the identity key for the SQLite history thread. This keeps the barrier to entry low: no passwords, no email, no session cookies. The trade-offs are intentional and accepted: two students who type the exact same name share a thread (we do not disambiguate "Ana" vs "Ana"), and there is no logout because there is no session."

The Dockerfile (`Dockerfile:63`) pre-creates `/app/data` with the right owner (UID 1000), but the DB file itself is ephemeral:

```dockerfile
# SQLite history dir: .dockerignore excludes data/ from the build context, so
# the dir is missing in the image. /app itself is owned by root with 0755
# (Docker WORKDIR default), so the runtime UID 1000 cannot create /app/data
# at boot. Pre-create it here with the right owner. The DB file itself is
# ephemeral (HF Spaces wipes disk on sleep) — accepted per AGENTS.md §7.12.
RUN mkdir -p /app/data && chown user:user /app/data
```

**What happens on sleep**:
1. HF Space is inactive for ~48h.
2. HF puts the Space to sleep; the ephemeral disk is wiped.
3. The SQLite file (`/app/data/historial.db`) is deleted.
4. Next visitor triggers a cold start; the container spins up; `init_db()` creates a fresh, empty SQLite file.
5. Student's name is still in `localStorage` (frontend fix A), so they're auto-identified.
6. But `GET /history?student_name=Ana` returns `[]` — the history is gone.

### 1.3 Frontend Fix A: Already Implemented

The orchestrator describes Fix A as: "localStorage remembers the student's display name across browser sessions. Tiny change in the chat HTML/JS."

**This is already done.** The code audit shows:

- `app/static/chat.js:28`: `let studentName = localStorage.getItem(STORAGE_KEY);`
- `app/static/chat.js:230`: `localStorage.setItem(STORAGE_KEY, name);`
- `app/static/chat.js:303-306`: On page load, if `studentName` is present, the name input is hidden and the chat is enabled.

**What Fix A does NOT do**: It does not preserve the conversation history. It only preserves the student's identity (display name). After a sleep, the student is auto-identified, but their history is empty.

**Conclusion**: Fix A is not a "fix" — it's already shipped. The real fix is Fix B (Turso migration).

### 1.4 Backend Fix B: Turso Migration

The orchestrator describes Fix B as: "migrate the conversation DB from SQLite-on-ephemeral-disk to Turso (libSQL, SQLite-compatible, free tier 9 GB, no sleep). DB lives outside the HF container."

**Current state**: The backend uses `sqlite3` stdlib to write to a local file (`rag/history.py`). The module is standalone — no imports from `rag/chain.py` or `app/main.py`. All public functions open and close their own connection.

**What needs to change**: Replace the local SQLite file with a remote Turso database. The schema, queries, and API remain identical (Turso is libSQL, which is SQLite-compatible). The only change is the connection string: instead of a file path, the backend connects to a Turso URL with an auth token.

**Why Turso**:
- SQLite-compatible: no schema changes, no query changes.
- Free tier: 9 GB storage, 100 GB transfer/month — more than enough for the prototype.
- No sleep: the database is external to the HF container; it persists regardless of HF's cold-start behavior.
- Simple: one env var for the URL, one for the auth token.

**Tradeoff paragraph (Turso vs. Supabase vs. Neon)**:
The orchestrator already decided Turso is the right pick. The rationale: Supabase and Neon are Postgres-based, which would require schema migration (SQLite → Postgres), query rewrites (SQLite-specific pragmas like `PRAGMA foreign_keys = ON` don't exist in Postgres), and a new ORM or raw SQL adapter. Turso is libSQL (SQLite-compatible), so the migration is a connection-string change, not a rewrite. For a prototype with a single developer and a 4-month timeline, Turso minimizes risk and effort. Supabase/Neon are better tools for production-scale Postgres, but the prototype doesn't need Postgres features (JSONB, full-text search, etc.). Turso's free tier is generous enough for the prototype's scale (~50-100 students, ~1000 messages/semester).

---

## 2. Affected Areas

| File | Why it's affected |
|------|-------------------|
| `rag/history.py` | Replace local SQLite file with Turso connection. Change `_db_path()` to return a Turso URL + auth token. All other functions (`init_db`, `get_or_create_student`, `save_message`, etc.) remain unchanged — Turso is SQLite-compatible. |
| `.env.example` | Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` env vars. Remove or deprecate `SQLITE_PATH` (or keep it as a fallback for local dev). |
| `requirements.txt` | Add `libsql-experimental` (Turso's Python driver) or use `sqlite3` with a remote connection (Turso supports both). |
| `Dockerfile` | No change needed — the backend code handles the connection. The `/app/data` directory is no longer used for history (but may still be used for other ephemeral data). |
| `AGENTS.md` | Update §7 decision #12 to document the Turso migration. Remove the "ephemeral disk" trade-off (it's no longer accepted — it's fixed). |
| `openspec/specs/conversation-persistence/spec.md` | Update the "Database file location and writability" requirement to reflect Turso. Remove the scenario "Directory is auto-created" (no longer relevant). Add a scenario "Turso connection is established on first request." |

**NOT affected**: `app/main.py`, `app/static/chat.js`, `app/static/index.html`, `app/static/style.css`, `rag/chain.py`, `rag/retrievers/*`, `rag/loaders/*`, `rag/splitters/*`, `rag/prompts/*`, `dashboard/*`.

---

## 3. Approaches

### Approach A: Frontend-Only (localStorage for History)

**Description**: Cache the conversation history in `localStorage` as a fallback. When the server returns an empty history (after a sleep), the frontend shows the cached version instead.

**How it works**:
1. On `POST /chat`, the frontend stores the user message and assistant response in `localStorage` (keyed by `student_name`).
2. On page load, the frontend fetches `GET /history?student_name=...`.
3. If the server returns `[]` (history lost), the frontend loads the cached history from `localStorage` and renders it.
4. The cached history is a best-effort backup — it's device-specific and can be cleared by the student.

**Pros**:
- No backend changes.
- No external dependencies (no Turso account, no network calls to a remote DB).
- The student sees their history even after a sleep (if they use the same device/browser).

**Cons**:
- Device-specific: if the student switches devices, the history is lost.
- Not a real fix: the server-side history is still lost. The frontend is just masking the problem.
- `localStorage` has a ~5 MB limit — large histories may not fit.
- Cache coherence: if the student uses multiple devices, the caches diverge.
- Violates AGENTS.md §3 ("History per student") — the history is tied to the device, not the student.

**Effort**: Low (2-3 days).

### Approach B: Backend Migration to Turso

**Description**: Replace the local SQLite file with a remote Turso database. The schema, queries, and API remain identical. The backend connects to Turso via a URL + auth token.

**How it works**:
1. Fabián creates a Turso account and database (free tier).
2. The backend is configured with `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` env vars.
3. `rag/history.py` is updated to connect to Turso instead of a local file.
4. The schema is migrated (or re-created) in Turso on first boot.
5. All existing endpoints (`POST /chat`, `GET /history`, `DELETE /messages/{id}`) work unchanged.

**Pros**:
- Real fix: the history persists across HF sleeps, device switches, and browser clears.
- SQLite-compatible: no schema changes, no query rewrites.
- Free tier is generous enough for the prototype.
- External to the HF container: no dependency on HF's ephemeral disk.
- Satisfies AGENTS.md §3 ("History per student") — the history is tied to the student, not the device.

**Cons**:
- Requires a Turso account (free, but still an external dependency).
- Network latency: every SQLite query is now a network call to Turso. For the prototype's scale (~50-100 students, ~1000 messages/semester), this is negligible (~10-50 ms per query).
- Turso's free tier has limits (9 GB storage, 100 GB transfer/month) — but the prototype won't hit them.

**Effort**: Medium (3-5 days).

### Approach C: HF Spaces Storage Bucket

**Description**: Use HF Spaces' Storage Bucket feature to persist the SQLite file across sleeps. The bucket is a persistent disk that survives cold starts.

**How it works**:
1. Fabián enables the Storage Bucket feature in the HF Space settings.
2. The SQLite file is written to the bucket instead of the ephemeral disk.
3. On cold start, the SQLite file is still there; the backend reconnects to it.

**Pros**:
- No external dependencies (no Turso, no Supabase, no Neon).
- The backend code remains unchanged (still uses local SQLite).
- Simple: just change the `SQLITE_PATH` env var to point to the bucket.

**Cons**:
- HF Spaces' Storage Bucket is a relatively new feature; documentation is sparse.
- The bucket is tied to the HF Space — if the Space is deleted, the bucket is lost.
- Not a "real" database: no replication, no backups, no point-in-time recovery.
- May have performance implications (network-attached storage vs. local disk).

**Effort**: Low (1-2 days) — but requires testing and validation.

### Approach D: Accept the Trade-Off (Do Nothing)

**Description**: Keep the current behavior. The history is lost on sleep, and that's OK for the prototype.

**Pros**:
- No work required.
- No external dependencies.
- The prototype is simple and easy to maintain.

**Cons**:
- Violates the team's desire to "fix it" (per the orchestrator's prompt).
- Students lose their history after a sleep — a poor user experience.
- Violates AGENTS.md §3 ("History per student") — the history is not truly persistent.

**Effort**: Zero.

---

## 4. Recommendation

**Fix A (frontend localStorage for history)**: Not recommended. It's a band-aid that masks the problem. The server-side history is still lost, and the frontend cache is device-specific. It also violates AGENTS.md §3 ("History per student") by tying the history to the device, not the student.

**Fix B (Turso migration)**: **Recommended**. It's the real fix. The history persists across sleeps, device switches, and browser clears. Turso is SQLite-compatible, so the migration is a connection-string change, not a rewrite. The free tier is generous enough for the prototype. The effort is medium (3-5 days), but the payoff is high: the prototype now has true conversation persistence.

**Approach C (HF Spaces Storage Bucket)**: Not recommended. It's a viable alternative, but Turso is a better tool for the job. The Storage Bucket is a relatively new feature with sparse documentation, and it's tied to the HF Space (if the Space is deleted, the bucket is lost). Turso is a dedicated database service with better guarantees.

**Approach D (do nothing)**: Not recommended. The team wants to fix the history loss, and this approach doesn't fix it.

**Final recommendation**: Proceed with Fix B (Turso migration). Fix A (frontend localStorage for name) is already shipped and requires no additional work.

---

## 5. Edge Cases

### 5.1 Student Closes Browser, Comes Back Tomorrow

**Before Fix B**: If the HF Space has slept (~48h inactivity), the SQLite file is wiped. The student's name is still in `localStorage`, so they're auto-identified. But `GET /history?student_name=Ana` returns `[]` — the history is gone.

**After Fix B**: The student's name is in `localStorage`, and the history is in Turso. `GET /history?student_name=Ana` returns the full history, regardless of whether the HF Space has slept. ✅

### 5.2 Two Students Share a Device

**Before Fix B**: The name is in `localStorage`. The second student sees the first student's history. ❌ (This is an accepted trade-off per AGENTS.md §7 decision #11 — typed-name identification is spoofable and not private.)

**After Fix B**: Same behavior. The name is in `localStorage`, and the history is in Turso. The second student still sees the first student's history. ❌ (Same trade-off.)

**Mitigation**: This is an accepted trade-off for the prototype. If it becomes a problem, a future change can replace typed-name identification with real auth (username + password, or token URL).

### 5.3 HF Cold Start with In-Flight History

**What happens**: The student sends a message. The backend starts streaming the response. The HF Space goes to sleep (or crashes). The student loses the response.

**Before Fix B**: The user message is persisted in SQLite (before Groq). The assistant message is not persisted (the stream didn't complete). On cold start, the SQLite file is wiped. The user message is lost.

**After Fix B**: The user message is persisted in Turso (before Groq). The assistant message is not persisted (the stream didn't complete). On cold start, the Turso database is still there. The user message is present; the assistant message is missing. The student can re-ask the question. ✅

**Mitigation**: The existing error-handling pattern in `app/main.py:142-148` catches exceptions and persists an error fallback message. This pattern works with Turso just as it works with local SQLite.

### 5.4 Large History

**What happens**: A student has 500+ messages persisted over a semester.

**Before Fix B**: The SQLite file grows. The `GET /history` endpoint returns all 500 messages. The frontend renders them all (no pagination). The Groq call injects only the last 10 messages (controlled by `HISTORY_WINDOW`).

**After Fix B**: Same behavior. The Turso database grows. The `GET /history` endpoint returns all 500 messages. The frontend renders them all (no pagination). The Groq call injects only the last 10 messages.

**Mitigation**: Pagination is out of scope for this change. If the history grows too large, a future change can add pagination to the frontend. The Groq call is unaffected (only the last N messages are injected).

### 5.5 Turso Service Disruption

**What happens**: Turso's service is down. The backend cannot connect to the database.

**Mitigation**: The backend should handle connection errors gracefully. If Turso is down, the backend should return a 503 (Service Unavailable) with a user-friendly error message. The frontend should display the error and suggest the student try again later. This is a standard error-handling pattern; the existing code in `app/main.py:142-148` already handles exceptions.

### 5.6 Turso Free Tier Limits

**What happens**: The prototype exceeds Turso's free tier limits (9 GB storage, 100 GB transfer/month).

**Mitigation**: The prototype won't hit these limits. ~50-100 students × ~1000 messages/semester × ~500 bytes/message = ~50 MB of storage. Transfer is ~100 GB/month, which is enough for ~10,000 requests/month (assuming ~10 KB per request). If the prototype grows beyond these limits, Fabián can upgrade to Turso's paid tier ($29/month for 100 GB storage, 1 TB transfer).

---

## 6. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Turso account setup fails** | WARNING | Fabián should create the account early and test the connection before starting the migration. If Turso doesn't work, fall back to Approach C (HF Spaces Storage Bucket). |
| **Turso network latency slows down the chat** | SUGGESTION | Unlikely at the prototype's scale. Test the latency with a few queries before and after the migration. If latency is a problem, consider caching the history in memory (but this defeats the purpose of Turso). |
| **Turso free tier limits are exceeded** | SUGGESTION | Monitor the usage via Turso's dashboard. If the prototype approaches the limits, upgrade to the paid tier ($29/month) or migrate to a self-hosted database. |
| **Schema migration fails** | WARNING | Turso is SQLite-compatible, so the schema should migrate without issues. Test the migration on a copy of the SQLite file before applying it to the production database. If the migration fails, fall back to local SQLite. |
| **Breaking the existing demo** | WARNING | The Turso migration is a connection-string change, not a rewrite. All existing endpoints and queries should work unchanged. Test the exact same queries from the last demo to ensure no regression. |
| **Turso service disruption** | WARNING | Handle connection errors gracefully. Return a 503 with a user-friendly error message. The frontend should display the error and suggest the student try again later. |
| **AGENTS.md §7 decision #12 is outdated** | SUGGESTION | Update the decision to document the Turso migration. Remove the "ephemeral disk" trade-off (it's no longer accepted — it's fixed). |
| **Cross-platform dev (macOS + Windows)** | SUGGESTION | Turso is a remote database; the dev environment doesn't matter. The backend code is unchanged (still uses `sqlite3` stdlib or `libsql-experimental`). Test on both platforms before deploying. |

---

## 7. Open Questions for Fabián

### OQ-1: Turso Account

Has Fabián created a Turso account? If not, he should do it early and test the connection before starting the migration.

**Context**: Turso's free tier is generous (9 GB storage, 100 GB transfer/month), but it requires an account. Fabián should create the account, create a database, and test the connection with a simple query before starting the migration.

**Recommendation**: Fabián should create the account and test the connection. If Turso doesn't work, fall back to Approach C (HF Spaces Storage Bucket).

### OQ-2: Local Dev vs. Deploy

Should the local dev environment use Turso or local SQLite?

**Context**: The current setup uses local SQLite (`data/historial.db`). If the backend is migrated to Turso, the local dev environment should also use Turso (to match the deploy environment). But this requires Fabián to have a Turso database for local dev, which may be inconvenient.

**Option A**: Use Turso for both local dev and deploy. The backend code is identical; only the env vars differ.

**Option B**: Use local SQLite for local dev, Turso for deploy. The backend code detects the environment and uses the appropriate connection. This adds complexity but keeps the local dev setup simple.

**Recommendation**: Option A (use Turso for both). The backend code is simpler, and the local dev environment matches the deploy environment. If Fabián wants to use local SQLite for local dev, he can set `SQLITE_PATH` in `.env` and the backend can detect it and use local SQLite. But this adds complexity.

### OQ-3: Schema Migration

Should the existing SQLite data be migrated to Turso, or should the Turso database start empty?

**Context**: The current SQLite file (`data/historial.db`) has data from the previous demos. If the data is important, it should be migrated to Turso. If the data is not important (it's just test data), the Turso database can start empty.

**Option A**: Migrate the existing data to Turso. This preserves the history from the previous demos.

**Option B**: Start with an empty Turso database. The existing data is lost, but the migration is simpler.

**Recommendation**: Option B (start empty). The existing data is test data from the previous demos; it's not important. If the data is important, Fabián can export it from SQLite and import it into Turso manually.

### OQ-4: AGENTS.md Update

Should AGENTS.md §7 decision #12 be updated to document the Turso migration?

**Context**: The current decision #12 says "HF Spaces via Docker SDK. The deploy is described by a `Dockerfile` plus a Space `README.md` with `sdk: docker` and `app_port: 7860`. The container runs as UID 1000, the embedding model is tracked via Git LFS, and pre-baked artifacts survive sleep/wake." It also says "The DB file itself is ephemeral (HF Spaces wipes disk on sleep) — accepted per AGENTS.md §7.12."

**Recommendation**: Yes, update decision #12 to document the Turso migration. Remove the "ephemeral disk" trade-off (it's no longer accepted — it's fixed). Add a note that the conversation history is now persisted in Turso, which is external to the HF container.

### OQ-5: Rollback Plan

What's the rollback plan if the Turso migration fails?

**Context**: If the Turso migration fails or causes issues, the backend should be able to fall back to local SQLite.

**Recommendation**: The rollback plan is to revert the commit(s) touching `rag/history.py`, `.env.example`, and `requirements.txt`. The backend will use local SQLite again. The Turso database is not deleted; it can be re-connected later if needed.

---

## 8. Cross-References to Existing Specs

### 8.1 conversation-persistence Spec

The `openspec/specs/conversation-persistence/spec.md` spec documents the SQLite schema, persistence lifecycle, history retrieval endpoint, message deletion endpoint, and history injection into Groq. All of these remain unchanged after the Turso migration. The only change is the "Database file location and writability" requirement, which currently says:

> "The SQLite file SHALL live at the path configured by `SQLITE_PATH` (default `./data/historial.db`) and SHALL be writable by the backend process."

This should be updated to:

> "The conversation history SHALL be persisted in a Turso database (libSQL, SQLite-compatible). The backend SHALL connect to Turso via the `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` environment variables. The schema, queries, and API are identical to the local SQLite setup."

The scenario "Directory is auto-created" is no longer relevant (Turso is a remote database). The scenario "Configure via env var" should be updated to reflect the Turso env vars.

### 8.2 student-identification Spec

The `openspec/specs/student-identification/spec.md` spec documents the typed-name identification flow. This spec is unchanged after the Turso migration. The identification flow is frontend-only (localStorage + `student_name` in request body); the backend resolution (lookup or create a `students` row) is unchanged.

### 8.3 socratic-guidance Spec

The `openspec/specs/socratic-guidance/spec.md` spec documents the Socratic layer. This spec is unchanged after the Turso migration. The history injection into Groq is unchanged; only the persistence layer (SQLite → Turso) is different.

---

## 9. Recommendation Summary

The exploration recommends **Fix B (Turso migration)**. Fix A (frontend localStorage for name) is already shipped and requires no additional work. The Turso migration is a connection-string change, not a rewrite. The schema, queries, and API remain identical. The free tier is generous enough for the prototype. The effort is medium (3-5 days), but the payoff is high: the prototype now has true conversation persistence across HF sleeps, device switches, and browser clears.

**Key decisions to make before the proposal**:
1. Has Fabián created a Turso account? (OQ-1)
2. Should the local dev environment use Turso or local SQLite? (OQ-2)
3. Should the existing SQLite data be migrated to Turso, or should the Turso database start empty? (OQ-3)
4. Should AGENTS.md §7 decision #12 be updated to document the Turso migration? (OQ-4)
5. What's the rollback plan if the Turso migration fails? (OQ-5)

**What the proposal should deliver**:
- A concrete Turso migration plan (schema, connection, env vars).
- A concrete rollback plan (revert to local SQLite).
- A concrete plan for updating AGENTS.md §7 decision #12.
- A concrete plan for updating the `conversation-persistence` spec.
- A concrete plan for testing the migration (before and after queries).
- A concrete plan for handling edge cases (Turso service disruption, free tier limits, large history).

---

## Ready for Proposal

**Yes.** The exploration has enough technical detail to feed the proposal phase. The open questions (OQ-1 through OQ-5) are operational, not architectural — they can be resolved during the proposal phase. The orchestrator should tell the user:

> "The persistent-history change is straightforward: the conversation history persistence layer is already complete (typed-name identification, SQLite schema, message persistence lifecycle, history injection into Groq, delete endpoints). The only gap is that SQLite lives on HF Spaces' ephemeral disk, so history is lost when the Space sleeps (~48h inactivity). Two fixes are proposed: (A) frontend localStorage for the student's display name — already shipped, no work needed; (B) backend migration to Turso — the real fix. Turso is SQLite-compatible, so the migration is a connection-string change, not a rewrite. The free tier (9 GB storage, 100 GB transfer/month) is generous enough for the prototype. The effort is medium (3-5 days). Before the proposal can proceed, Fabián must answer 5 operational questions (OQ-1 through OQ-5) — the most critical being: has he created a Turso account, and should the local dev environment use Turso or local SQLite?"

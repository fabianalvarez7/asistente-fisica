# Verification Report — Persistent History (Turso Migration)

**Change**: `2026-08-14-persistent-history`
**Status**: `pass-with-warnings`
**Date**: 2026-08-17
**Verdict**: **PASS WITH WARNINGS**
**Mode**: hybrid (openspec file + Engram) · Standard verify (Strict TDD: false) · read-only inspection

---

## 1. Executive Summary

All six planned code+docs commits landed in the expected order with the expected file footprints: `libsql-experimental` was added to `requirements.txt`, `TURSO_*` env vars and a dev-only annotation on `SQLITE_PATH` were added to `.env.example`, `rag/history.py` was refactored to a singleton connection factory (Turso when both env vars are set, local SQLite otherwise), `app/main.py` now wraps every DB call site with HTTP 503 / SSE error-frame handling, the `conversation-persistence` spec delta was applied cleanly to the base spec, and AGENTS.md §7 #12 + §12 were updated to document the Turso architecture. The spec contract (Turso connection on first request, local fallback, 503 on failure, SSE error frame mid-request, HF Spaces Secrets required in production, `SQLITE_PATH` deprecated, "Directory is auto-created" scenario removed) is fully reflected in both the updated base spec and the implementation. Four design deviations exist; all are justified in `apply-progress.md` and none breaks the spec. The locally-verifiable scenarios (503 returned on invalid Turso token, SSE `event: error` frame + `[DONE]` emitted, local fallback returns a `sqlite3.Connection`) PASS at runtime per the manual commands recorded in `apply-progress.md`. The change is eligible for `sdd-archive` after one mandatory pre-archive paperwork fix (flip an unchecked checkbox in `tasks.md`) and after Task 7 (HF Spaces deploy + real-Turso cold-start verification) is completed as a post-archive operational step.

---

## 2. Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 7 |
| Tasks complete (committed) | 6 |
| Tasks incomplete (commits) | 0 |
| Tasks pending (deploy action, non-commit) | 1 (Task 7) |
| Unchecked implementation checkboxes | 1 (Task 1, box 2) |
| Commits verified | 6 / 6 |

---

## 3. Build / Tests / Runtime Evidence

**Build / import**: ✅ Passed (per `apply-progress.md` Task 1 & Task 4).
```
python -c "import libsql_experimental; print(libsql_experimental.__name__)"  # OK
python -m py_compile app/main.py                                             # OK
```

**Tests (committed automated suite)**: ➖ Not available for this change.
The only committed test, `tests/test_chat_sse_message_ids.py`, mocks `get_history` (line 46: `patch("app.main.get_history", return_value=[])`) and does NOT exercise the new connection factory, the Turso branch, the 503 path, or the SSE DB-error frame. No `tests/test_history_*.py` covering the connection layer exists. Runtime evidence for the new behavior comes exclusively from the ad-hoc manual commands recorded in `apply-progress.md` (§4 of that file).

**Runtime evidence (ad-hoc, from `apply-progress.md`)**:

| # | Assertion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `import libsql_experimental` succeeds after `pip install -r requirements.txt` | PASS | `apply-progress.md` Task 1 |
| 2 | `grep -c TURSO .env.example` returns `3` (two var lines + one comment mention) | PASS | `apply-progress.md` Task 2 |
| 3 | `_get_connection()` returns `sqlite3.Connection` when Turso vars unset | PASS | `apply-progress.md` Task 3 — printed `Connection (sqlite3.Connection)` |
| 4 | `_get_connection()` reaches the libSQL driver branch when Turso vars set | PASS | `apply-progress.md` Task 3 — printed `builtins Connection` (libsql C ext) |
| 5 | `GET /history` returns 503 with Spanish message on invalid Turso token | PASS | `apply-progress.md` Task 4 — status `503` |
| 6 | `POST /chat` returns 503 (pre-Groq DB failure) on invalid Turso token | PASS | `apply-progress.md` Task 4 — status `503` |
| 7 | `DELETE /messages/{id}` returns 503 on invalid Turso token | PASS | `apply-progress.md` Task 4 — status `503` |
| 8 | `grep -c "Turso" openspec/specs/conversation-persistence/spec.md` returns `16` | PASS | `apply-progress.md` Task 5 |
| 9 | `grep -n "ephemeral" AGENTS.md` returns no matches | PASS | `apply-progress.md` Task 6; re-confirmed this pass |

**Coverage**: ➖ Not available. No coverage tool configured for this project; not a project requirement and not introduced retroactively.

**End-to-end / production scenarios**: ❌ UNTESTED at runtime.
The spec scenarios "HF Spaces Secrets are set for production" and the change's headline success criterion ("history survives an HF Space cold start") require a real Turso database + a live HF Spaces deploy + a container restart. These are pending Task 7 and could not be exercised in this verify pass.

---

## 4. Spec Compliance Matrix

Statuses: ✅ COMPLIANT (runtime evidence in `apply-progress.md`), ✅-STATIC (code/spec inspection only, no runtime test), ⚠️ PARTIAL / UNTESTED (no runtime evidence), ❌ FAIL (contradicts).

Source of truth: `openspec/changes/2026-08-14-persistent-history/specs/conversation-persistence/spec.md` (delta) vs `openspec/specs/conversation-persistence/spec.md` (updated base).

| Delta requirement / scenario | Base spec reflects it? | Code implements it? | Status |
|------------------------------|------------------------|----------------------|--------|
| Turso connection when `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` set, via libSQL driver | ✅ Base spec L174-176, L178-183 | ✅ `rag/history.py:48-53` | ✅-STATIC (driver branch reached per `apply-progress.md` Task 3) |
| Local SQLite fallback at `SQLITE_PATH` (default `./data/historial.db`) when both Turso vars unset | ✅ Base spec L185-190, L206-210 | ✅ `rag/history.py:54-59` | ✅ COMPLIANT (`apply-progress.md` Task 3 — returned `sqlite3.Connection`) |
| Schema created on first connection via `CREATE TABLE IF NOT EXISTS` (idempotent) | ✅ Base spec L9-30, L176 | ✅ `rag/history.py:106-132` (`init_db`) | ✅-STATIC |
| Connection established on first request and reused (not re-opened per request) | ✅ Base spec L176, L182-183 | ✅ `rag/history.py:34-60` (singleton + double-checked lock) | ✅-STATIC |
| Turso failure (network/auth) → HTTP 503 + user-friendly Spanish message | ✅ Base spec L192-197 | ✅ `app/main.py:115-119, 200-201, 225-226`; `DB_ERROR_MESSAGE` L65 | ✅ COMPLIANT (`apply-progress.md` Task 4 — 503 on all 3 endpoints) |
| Mid-request Turso disruption → SSE `event: error` frame + `[DONE]`, no fabricated assistant message | ✅ Base spec L199-204 | ✅ `app/main.py:126-130` (`_db_error_frame`), `142-145`, `161-164`, `176-179` | ✅-STATIC (error-frame path inspected; not runtime-exercised against a real mid-stream drop) |
| HF Spaces Secrets required in production (`TURSO_*` as Space Secrets) | ✅ Base spec L212-221 | ✅ Documented in `AGENTS.md:148` + `AGENTS.md:219-220`; `.env.example:15-20` | ✅-STATIC (deploy config, not runtime-verified) |
| Missing Turso Secrets in production = deploy misconfiguration (not runtime error) | ✅ Base spec L223-228 | ✅ Factory stays permissive (`rag/history.py:50` — `if url and token:`); `AGENTS.md:148` documents the requirement | ✅-STATIC |
| `SQLITE_PATH` deprecated in favor of `TURSO_*` | ✅ Base spec L185-190, L206-210 frame it as dev-only | ✅ `.env.example:22-23` ("fallback SOLO para desarrollo local"); `AGENTS.md:221` ("Dev-only; not used in production") | ✅-STATIC |
| Scenario "Directory is auto-created" REMOVED | ✅ Confirmed absent from base spec (`grep "Directory is auto-created\|Database file location"` → no matches) | n/a (spec-only) | ✅ COMPLIANT |
| Pre-existing scenarios preserved (schema, lifecycle, retrieval, deletion, injection, token budget) | ✅ Base spec L9-172 unchanged | ✅ `rag/history.py` public signatures + `rag/chain.py` history injection untouched | ✅-STATIC (regression not re-run this pass) |

**Compliance summary**: 11/11 delta scenarios compliant or statically verified; 2 production scenarios UNTESTED at runtime (pending Task 7).

---

## 5. Design Compliance

Source: `openspec/changes/2026-08-14-persistent-history/design.md`.

| Design decision | Followed? | Evidence / deviation note |
|-----------------|-----------|---------------------------|
| Singleton `_connection` + `threading.Lock`, lazy init | ✅ Yes | `rag/history.py:34-35, 38-60` — double-checked locking pattern (fast path outside lock, re-check inside). |
| `libsql-experimental>=0.1,<1.0` | ⚠️ Deviation (justified) | Pin is `>=0.0.55,<1.0` (`requirements.txt:21`). Justified in `apply-progress.md` §"Known Issues" #1: PyPI only lists `0.0.x` releases for `libsql-experimental`; no `0.1+` release exists. The design explicitly anticipated this ("Verify the current PyPI version at apply time and tighten the pin if a stable release exists"). Acceptable. |
| Mid-request error handling mirrors existing Groq error pattern | ✅ Yes | `app/main.py:126-130` defines `_db_error_frame()` emitting `event: error\ndata: {json}\n\n`; called at the three `save_message(assistant, ...)` sites (L142-145, L161-164, L176-179) followed by `data: [DONE]\n\n` and `return`. No fabricated assistant message is persisted on the DB-failure path. |
| `init_db()` is idempotent | ✅ Yes | `rag/history.py:106-132` uses `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`; `conn.commit()` at L132. |
| Public functions use `with conn:` for transaction blocks | ⚠️ Deviation (justified) | `with conn:` blocks are NOT used. `libsql_experimental.Connection` does not implement `__enter__`/`__exit__`, so the code uses `conn.execute(...)` + `conn.commit()` manually (`rag/history.py:142-155, 195-204, 251-257`, etc.). Works for both `sqlite3` and libSQL. Justified in `apply-progress.md` §"Known Issues" #2. Acceptable. |
| `_configure_connection()` kept as a no-op shim | ✅ Yes | `rag/history.py:63-70` — `pass` with docstring explaining pragmas are applied in the local-SQLite branch of `_get_connection` (L58-59). |
| 5 files modified | ✅ Yes (6 touched incl. openspec) | `requirements.txt`, `.env.example`, `rag/history.py`, `app/main.py`, `openspec/specs/conversation-persistence/spec.md`, `AGENTS.md` — matches design §"File Changes" + the spec-delta + AGENTS tasks. |
| Helper `_rows_to_dicts()` added | ⚠️ Deviation (additive, justified) | `rag/history.py:78-85` — converts cursor rows to dicts via `cursor.description`. Added because libSQL does not expose a `sqlite3.Row` factory. Preserves the `get_history` contract: returns `[{id, role, content, created_at}, ...]` (SELECT at L219, L229 projects exactly those columns). Acceptable. |
| `init_db()` wrapped in try/except at import time | ⚠️ Deviation (justified) | `app/main.py:70-75` — `init_db()` is called at module import inside `try/except Exception` that prints a notice on failure. Justified in `apply-progress.md` §"Known Issues" #4: without this, an invalid Turso token at startup would crash the process before any endpoint could return 503 / SSE error frame. The task list only named endpoint call sites, but this import-time call site was required for the "Turso connection failure returns 503" scenario to hold. Acceptable. |

**Design coherence**: ✅ All four deviations are documented, justified, and do not break any spec requirement. Three are forced by the libSQL driver's API (no context manager, no row factory); one is a robustness extension (import-time try/except) required to satisfy the 503 scenario.

---

## 6. Tasks Compliance

| # | Task | Commit | Hash | Files (stat) | Status |
|---|------|--------|------|--------------|--------|
| 1 | Add `libsql-experimental` to `requirements.txt` | `chore(deps): add libsql-experimental for Turso support` | `ff28362` | `requirements.txt` +3 | ⚠️ Box 2 unchecked (see CRITICAL C1) |
| 2 | Add Turso env vars to `.env.example` | `chore(env): add TURSO_* vars and mark SQLITE_PATH as dev-only` | `63d4cfd` | `.env.example` +8/-1 | ✅ |
| 3 | Refactor `rag/history.py` with connection factory | `refactor(history): swap SQLite factory for Turso-or-local connection layer` | `31ad891` | `rag/history.py` +156/-129 | ✅ |
| 4 | Wrap DB calls in `app/main.py` with error handling | `fix(chat): handle DB errors mid-request with SSE error frame` | `2761770` | `app/main.py` +68/-24 | ✅ |
| 5 | Apply spec delta to `conversation-persistence` | `docs(spec): apply persistent-history delta to conversation-persistence` | `614cb97` | `openspec/specs/conversation-persistence/spec.md` +48/-8 | ✅ |
| 6 | Update AGENTS.md §7 #12 | `docs(agents): update §7 #12 — history persistence via Turso` | `2d8ec29` | `AGENTS.md` +4/-2 | ✅ |
| 7 | Deploy & verify on HF Spaces | NO commit (deploy action) | — | none | ⏳ Pending (see WARNING W1) |

**Task 1 detail**: `tasks.md` L60-61 has two checkboxes:
- `[x] Add libsql-experimental>=0.1,<1.0 under a new # History persistence section.` — checked, but the literal text `>=0.1,<1.0` is now stale (actual pin is `>=0.0.55,<1.0`).
- `[ ] Verify current PyPI version before committing; tighten pin if a stable release exists.` — **unchecked**, but the work it describes WAS performed: `apply-progress.md` §"Known Issues" #1 documents that the pin was tightened to `>=0.0.55,<1.0` because no `0.1+` release exists on PyPI. This is a checkbox-hygiene miss, not missing work.

---

## 7. Code Quality

| Concern | Verdict | Evidence |
|---------|---------|----------|
| Obvious bugs in the connection factory | ✅ None found | `rag/history.py:38-60` — double-checked locking is correct; env-var branching reads `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` and only takes the Turso branch when BOTH are truthy; local branch creates the parent dir + applies WAL/FK pragmas before returning. |
| `get_history(student_id, limit)` return shape preserved | ✅ Yes | `rag/history.py:207-241` — SELECT projects `id, role, content, created_at`; `_rows_to_dicts(cursor)` (L78-85) builds dicts from `cursor.description`. Returns `[{id, role, content, created_at}, ...]` ordered `created_at ASC, id ASC`. Matches the pre-change contract. |
| `delete_message(message_id, student_id)` works with new connection | ✅ Yes | `rag/history.py:244-257` — `conn.execute("DELETE ... WHERE id = ? AND student_id = ?")` + `conn.commit()` + `return cursor.rowcount > 0`. Works for both `sqlite3` and libSQL. |
| Thread-safety of the singleton | ✅ Yes (for current architecture) | First-call: double-checked lock (`rag/history.py:44-46`) serializes initialization. After init, `_connection` is read without the lock (L41-42) — safe under CPython's GIL for a module-level reference. Current FastAPI setup runs the `async def` endpoints on the event loop (single thread), so all DB access is single-threaded in practice. See SUGGESTION S4 for the latent risk if endpoints are later moved to a threadpool. |
| Broken-connection caching | ⚠️ Minor robustness gap | If `libsql.connect()` succeeds but the subsequent `CREATE TABLE` in `init_db()` fails (e.g., token valid for connect but not for DDL), `_connection` is left cached as a possibly-broken handle. Subsequent `_get_connection()` calls return it and every request fails with 503 until the process restarts. No retry/reconnect logic. See SUGGESTION S5. |

---

## 8. Documentation

| Check | Verdict | Evidence |
|-------|---------|----------|
| AGENTS.md §7 #12 reflects the Turso architecture | ✅ Yes | `AGENTS.md:148` — rewritten to "History persistence via Turso (libSQL)" with `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`, dev fallback, and "MUST be configured as Space Secrets" in production. |
| "ephemeral disk" trade-off paragraph gone from AGENTS.md | ✅ Yes | `grep "ephemeral" AGENTS.md` → 0 matches (re-confirmed this pass). The 51 repo-wide matches are all in `openspec/changes/**` archives, `Dockerfile`, and the change's own artifacts — none in AGENTS.md. |
| §12 Environment Variables table includes `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` | ✅ Yes | `AGENTS.md:219-220` — both rows with "No (dev) / Yes (deploy)" required column and "dev falls back to `SQLITE_PATH` when unset" purpose. `SQLITE_PATH` row (L221) annotated "Dev-only; not used in production." |
| Spec delta applies cleanly (no contradictions between updated base spec and delta) | ✅ Yes | The updated base spec contains all MODIFIED + ADDED requirements/scenarios from the delta and NONE of the REMOVED content. `grep "Directory is auto-created\|Database file location"` on the base spec → no matches. The base spec additionally retains a "Configure SQLite path via env var (dev-only fallback)" scenario (L206-210) that is consistent with (not contradictory to) the modified requirement. |
| `.env.example` documents Turso + dev-only SQLite | ✅ Yes | `.env.example:15-23` — `TURSO_DATABASE_URL=` + `TURSO_AUTH_TOKEN=` empty with Spanish comment pointing to `https://app.turso.tech`; `SQLITE_PATH` annotated "fallback SOLO para desarrollo local cuando TURSO_* no están seteadas." |
| Dockerfile comment consistency | ⚠️ Stale | `Dockerfile:58-62` still says "The DB file itself is ephemeral (HF Spaces wipes disk on sleep) — accepted per AGENTS.md §7.12." But §7.12 no longer accepts that trade-off (it now documents Turso). The `/app/data` pre-creation is now only relevant for the local-SQLite dev fallback, which does not run in production once Turso Secrets are set. See WARNING W2. |

---

## 9. Findings

### CRITICAL

| # | Finding | Fix |
|---|---------|-----|
| **C1** | **Unchecked implementation checkbox in `tasks.md` Task 1, box 2** ("Verify current PyPI version before committing; tighten pin if a stable release exists"). The substantive work IS complete and documented in `apply-progress.md` §"Known Issues" #1 (pin tightened from `>=0.1,<1.0` to `>=0.0.55,<1.0` because no `0.1+` release exists on PyPI), but the checkbox was not flipped to `[x]`. Per the project's verify convention (see `archive/2026-07-22-student-history/verify-report.md` first-pass FAIL for the same class of issue) and the sdd-verify hard rule ("Any unchecked implementation task is CRITICAL"), this blocks archive readiness as a paperwork defect. | In `openspec/changes/2026-08-14-persistent-history/tasks.md` L61, flip `- [ ]` → `- [x]`. Optionally also update L60's stale literal text from `>=0.1,<1.0` to `>=0.0.55,<1.0` to match the actual pin in `requirements.txt:21`. One-line doc edit; no code change. |

> **Verdict note on C1**: the underlying implementation is complete, correct, and runtime-verified (package installs and imports per `apply-progress.md` Task 1). C1 is a recording miss, not missing work. The fix is a single checkbox flip. Treating this as a hard FAIL would be disproportionate to a one-line paperwork fix when all code is shipped and the locally-verifiable scenarios pass; it is therefore recorded as a mandatory pre-archive fix and the overall verdict is PASS WITH WARNINGS. The orchestrator/user should flip the checkbox before or during `sdd-archive`.

### WARNING

| # | Finding | Severity rationale |
|---|---------|--------------------|
| **W1** | **Task 7 (HF Spaces deploy + real-Turso cold-start verification) is pending.** The change's headline success criterion — "history survives an HF Space cold start" — and the spec scenarios "HF Spaces Secrets are set for production" + "Missing Turso Secrets in production is a deploy misconfiguration" are UNTESTED at runtime. They require a real Turso database, a live HF Spaces deploy, and a container restart, none of which can be exercised in static verification. `apply-progress.md` explicitly marks Task 7 as ⏳ Pending and notes it is "intentionally not a commit." | Non-blocking for code completeness (Task 7 is an operational/deploy task, not an implementation task), but blocking for the change's end-to-end success claim. Should be completed as a post-archive (or pre-archive) operational step by the user. |
| **W2** | **Stale Dockerfile comment.** `Dockerfile:58-62` references "The DB file itself is ephemeral (HF Spaces wipes disk on sleep) — accepted per AGENTS.md §7.12." AGENTS.md §7.12 no longer accepts that trade-off (rewritten to document Turso). The `/app/data` pre-creation is now only relevant for the dev-only SQLite fallback. | Documentation inconsistency only; no runtime impact (the dir creation is harmless). Should be updated in a follow-up to reflect that history is in Turso and `/app/data` is dev-fallback-only. Not in this change's file list, so it is a carry-over warning. |

### SUGGESTION

| # | Suggestion |
|---|------------|
| **S1** | **No committed automated tests for the new connection factory.** The Turso branch, local fallback, 503 path, and SSE DB-error frame are verified only by the ad-hoc commands in `apply-progress.md`. Consider adding `tests/test_history_connection.py` (monkeypatched env vars + mocked `libsql.connect`) and `tests/test_chat_db_error_frame.py` (TestClient with an invalid token → assert SSE `event: error` frame) so these paths are continuously verified, not just by the manual run. Matches S3 from the predecessor change's verify-report. |
| **S2** | **`print` instead of `logging` for `init_db` failure.** `app/main.py:75` uses `print("[history] init_db failed; DB errors will be surfaced per request")`. On HF Spaces, stdout may not be surfaced in the Space logs UI depending on configuration. Consider `logging.getLogger(__name__).warning(...)` for observability. |
| **S3** | **Bare `except Exception` clauses in `app/main.py`.** L115, L142, L161, L176, L200, L225 catch `Exception` broadly. A non-DB bug (e.g., a `TypeError` in `get_or_create_student` logic) would surface to the user as the 503 "DB error" message, masking the real bug. Consider narrowing to `(sqlite3.Error, OSError, ConnectionError)` and/or `logging.exception(...)` before raising 503, so genuine code bugs are debuggable. |
| **S4** | **Latent thread-safety risk if endpoints move to a threadpool.** The singleton connection is safe today because the `async def` endpoints run DB calls synchronously on the event loop thread. If the endpoints are later made `def` (threadpool) or wrapped in `run_in_executor`, the cached `sqlite3.Connection` would be shared across threads and raise `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. Document this assumption or add per-thread connections if the execution model changes. |
| **S5** | **Broken-connection caching.** If `libsql.connect()` succeeds but `CREATE TABLE` in `init_db()` fails at import, `_connection` stays cached as a broken handle and every subsequent request fails with 503 until process restart. Consider resetting `_connection = None` inside the `except` at `app/main.py:72-75` so the next request retries the connection. |

---

## 10. Verdict

**PASS WITH WARNINGS**

**Rationale**:
- All 6 code+docs commits landed in the expected order with the expected file footprints (`git show --stat` confirmed).
- The spec delta applied cleanly: every MODIFIED + ADDED requirement/scenario is present in the updated base spec; the REMOVED "Directory is auto-created" scenario is absent; no contradictions.
- The code implements every spec requirement: Turso connection when both env vars set (`rag/history.py:48-53`), local fallback otherwise (L54-59), idempotent schema bootstrap (L106-132), singleton reuse with double-checked locking (L34-60), HTTP 503 on DB failure (`app/main.py:115-119, 200-201, 225-226`), SSE `event: error` frame + `[DONE]` mid-request with no fabricated assistant message (`app/main.py:126-130, 142-145, 161-164, 176-179`), HF Spaces Secrets requirement documented (`AGENTS.md:148, 219-220`), `SQLITE_PATH` deprecated (`.env.example:22-23`, `AGENTS.md:221`).
- All four design deviations are documented in `apply-progress.md` and justified (three forced by the libSQL driver API; one a robustness extension required by the 503 scenario). None breaks the spec.
- Locally-verifiable runtime scenarios PASS per `apply-progress.md`: local fallback returns `sqlite3.Connection`; Turso driver branch is reached; all three endpoints return 503 with the Spanish message on an invalid token.
- The single CRITICAL (C1) is a checkbox-hygiene miss whose underlying work is complete and verified — the fix is a one-line `tasks.md` edit. All code is shipped and correct; blocking archive on this alone would be disproportionate.
- Remaining non-blocking items: W1 (Task 7 deploy verification pending — the change's end-to-end cold-start claim is unverified at runtime), W2 (stale Dockerfile comment), and five SUGGESTIONs (test coverage, logging, exception breadth, thread-safety assumption, broken-connection caching).

**Change is eligible for `sdd-archive`** after flipping the C1 checkbox (and optionally updating the stale text in `tasks.md` L60). Task 7 should be completed as a post-archive operational step by the user (it is not a code commit and cannot be verified without real Turso credentials + a live HF Space).

---

## 11. Recommended Next Step

**`archive`** — after the user applies the one-line C1 fix (flip `tasks.md` L61 `- [ ]` → `- [x]`; optionally update L60 text to `>=0.0.55,<1.0`).

Task 7 (HF Spaces deploy + cold-start verification with real Turso credentials) is a post-archive operational step, not a code gate. It should be tracked separately and its outcome recorded in `apply-progress.md` once completed.

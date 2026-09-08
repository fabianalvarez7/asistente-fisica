# Archive Report: Persistent History (Turso Migration)

> **Change**: `2026-08-14-persistent-history`
> **Status**: archived
> **Predecessor**: `2026-07-22-student-history`

## Summary

The persistent-history change ships the migration of conversation history from local SQLite (HF Spaces ephemeral disk) to Turso (libSQL remote DB). All 7 commits landed in order. Verify phase passed with two WARNINGs — one CRITICAL paperwork miss (unchecked checkbox in `tasks.md`, fixed before archive) and one doc drift (stale Dockerfile comment, fixed in commit `3f5a305`). The end-to-end deploy verification (Task 7) is a pending operational step the user must run on HF Spaces.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `ff28362` | chore(deps): add libsql-experimental for Turso support |
| 2 | `63d4cfd` | chore(env): add TURSO_* vars and mark SQLITE_PATH as dev-only |
| 3 | `31ad891` | refactor(history): swap SQLite factory for Turso-or-local connection layer |
| 4 | `2761770` | fix(chat): handle DB errors mid-request with SSE error frame |
| 5 | `614cb97` | docs(spec): apply persistent-history delta to conversation-persistence |
| 6 | `2d8ec29` | docs(agents): update §7 #12 — history persistence via Turso |
| 7 | `3f5a305` | docs(dockerfile): update /app/data comment to reflect Turso history persistence |

## Files Affected

| File | Action |
|------|--------|
| `requirements.txt` | modify — added `libsql-experimental>=0.0.55,<1.0` |
| `.env.example` | modify — added `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN`, marked `SQLITE_PATH` dev-only |
| `rag/history.py` | modify — replaced `_db_path()` with `_get_connection()` factory (singleton + lock) |
| `app/main.py` | modify — wrapped DB calls with 503 / SSE error frame handling |
| `openspec/specs/conversation-persistence/spec.md` | modify — applied delta (Turso as production DB) |
| `AGENTS.md` | modify — §7 #12 rewritten, §12 env table updated |
| `Dockerfile` | modify — comment updated to reflect Turso architecture |

## Specs Modified

- `conversation-persistence` — delta applied. The base spec now reflects Turso as the production DB; local SQLite is dev-only fallback. Scenario "Directory is auto-created" removed. New scenarios added: Turso connection on first request, local SQLite fallback, Turso connection failure returns 503, Turso service disruption mid-request, HF Spaces Secrets required in production.

## AGENTS.md Drift

- §7 decision #12 rewritten — removes the "ephemeral disk accepted" trade-off paragraph; documents the Turso migration and the HF Spaces Secrets requirement.
- §12 Environment Variables table — added `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` rows.

## Deviations from Design (carry-over from apply)

1. Package pin: `>=0.0.55,<1.0` instead of `>=0.1,<1.0` (no `0.1+` release exists on PyPI yet). Recorded in `tasks.md` after verify-report.
2. No `with conn:` blocks in `rag/history.py` — `libsql_experimental.Connection` does not implement context manager. Manual `execute` + `commit` used instead.
3. Helper `_rows_to_dicts(cursor)` added because libSQL does not expose a `Row` factory like `sqlite3.Row`.
4. `init_db()` wrapped in `try/except` at import time so a misconfigured Turso in production does not crash the process before endpoints can return 503.

## Operational Follow-Up

- **Task 7 — Deploy and verify on HF Spaces** (pending):
  1. Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as HF Space Secrets.
  2. Push the new commits to the HF Space repo per `docs/hf-space.md`.
  3. Send a chat message; verify the row exists in Turso via the dashboard or `turso db shell`.
  4. Cold-restart the Space (Settings → Restart). Send another message. Verify the first message is in `GET /history`.

  Acceptance: history survives an HF Space cold start. Until this is verified end-to-end, the change's headline claim ("no more history loss on sleep") is operationally unproven.

## Cross-References

- `explore.md` — full exploration (384 lines).
- `proposal.md` — change proposal (154 lines).
- `specs/conversation-persistence/spec.md` — the delta spec applied in this change.
- `design.md` — technical design (1149 words).
- `tasks.md` — implementation plan (199 lines, 7 tasks).
- `apply-progress.md` — what landed.
- `verify-report.md` — verification (PASS WITH WARNINGS, 1 CRITICAL + 2 WARNINGs).
- Predecessor: `2026-07-22-student-history` (archived).
- Updated: `openspec/specs/conversation-persistence/spec.md` (base spec).
- Updated: `AGENTS.md` §7 #12 + §12.

## Notes for Future Devs

- `libsql-experimental` is a thin wrapper; if Turso ships a stable `libsql` package, consider migrating.
- The factory is permissive: a misconfigured HF Space (no Turso Secrets) will silently fall back to local SQLite and lose history on sleep. Documented in AGENTS.md §7 #12 as a deploy misconfiguration, not a runtime error.
- The `try/except` around `init_db()` at import time is intentional — it preserves the "fail at first request with 503" contract even when the DB is misconfigured.

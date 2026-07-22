# Archive Report: Student History & Basic Identification

**Change**: `student-history`
**Archived**: 2026-07-22
**Archive path**: `openspec/changes/archive/2026-07-22-student-history/`
**Artifact store mode**: openspec
**Branch**: `feat/student-history`
**Orchestrator instruction**: do NOT commit file moves (orchestrator will handle staging and committing)

---

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| student-identification | **Created** (new main spec) | 7 requirements, 11 scenarios — copied from delta spec (no prior main spec existed) |
| conversation-persistence | **Created** (new main spec) | 8 requirements, 14 scenarios — copied from delta spec (no prior main spec existed) |
| socratic-guidance | **Updated** (merged delta) | 1 requirement MODIFIED ("Single-turn behaviour is enforced"), 1 requirement ADDED ("History is visible to the model without breaking Socratic guidance"), 3 scenarios added to modified req, 3 scenarios for new req, Out of Scope section updated to reflect that conversation history is now in scope at the infrastructure level |

### Merge details for `openspec/specs/socratic-guidance/spec.md`

**MODIFIED** — `"Single-turn behaviour is enforced"` (replaced entirely):
- The requirement now acknowledges that the model CAN see prior history (injected between `_FEW_SHOT` and current query per the `conversation-persistence` capability), but the pedagogical behaviour SHALL NOT exploit visibility to escalate hints, hand out answers, or skip ladder rungs.
- Third scenario added: "History does not unlock answer leakage" — explicit guard against answer leakage via history.
- Previously: "Each request was independent, the model could not see prior history."

**ADDED** — `"History is visible to the model without breaking Socratic guidance"` (appended after all existing requirements, before Open Questions Resolved):
- Declares that Socratic pedagogy continues to hold in the presence of injected history.
- Multi-turn pedagogical adaptation is explicitly out of scope for this change.

**Out of Scope updated**: Conversation history is no longer listed as out of scope (it is now in scope via the `conversation-persistence` capability). Multi-turn Socratic adaptation remains out of scope and is now explicitly named. Student identification is referenced to the `student-identification` capability.

---

## Archive Contents

| Artifact | Status |
|----------|--------|
| `proposal.md` | ✅ Present |
| `design.md` | ✅ Present |
| `explore.md` | ✅ Present |
| `specs/student-identification/spec.md` | ✅ Present (delta spec) |
| `specs/conversation-persistence/spec.md` | ✅ Present (delta spec) |
| `specs/socratic-guidance/spec.md` | ✅ Present (delta spec) |
| `tasks.md` | ✅ Present (6/6 tasks marked complete) |
| `apply-progress.md` | ✅ Present (full apply lifecycle documented) |
| `verify-report.md` | ✅ Present |

---

## Task Completion Gate Assessment

All 6 implementation tasks are marked `[x]` in `tasks.md`:

| Task | Type | Checkbox | Actual Status |
|------|------|----------|---------------|
| 1 — `rag/history.py` SQLite module | Implementation | `[x]` | Complete (commit `42d61a4`) |
| 2 — `rag/chain.py` history injection | Implementation | `[x]` | Complete (commit `58fe5aa`) |
| 3 — FastAPI endpoints + persistence lifecycle | Implementation | `[x]` | Complete (commit `9cb7d6a`, plus fix commits `ec021b0`/`48eac7e`) |
| 4 — Frontend name gate, history, delete buttons | Implementation | `[x]` | Complete (commits `d3513f0`/`c56d840`) |
| 5 — Config & docs (`HISTORY_WINDOW`, AGENTS.md) | Implementation | `[x]` | Complete (commit `e9deb57`) |
| 6 — Manual 10-case test run | Implementation | `[x]` | Complete — 10/10 PASS on 2026-07-21 (commit `6d2ab50`) |

**Verdict**: All implementation tasks complete. No stale checkboxes on implementation tasks. Gate passes.

---

## Verification Status

**Verdict**: **PASS WITH WARNINGS** (as recorded in `verify-report.md`)

- No CRITICAL issues remain (single first-pass CRITICAL — unchecked Task 6 boxes — was cleared in re-verification).
- Unit test `tests.test_chat_sse_message_ids` passes (1/1 OK).
- 9 runtime API/smoke assertions all PASS.
- Remaining issues are non-blocking WARNINGs only:

### Warnings (carried over by design)

| # | Warning | Status |
|---|---------|--------|
| W1 | **Review Workload Guard breach.** Code-only delta ~+600/-21 exceeds 400-line budget. Openspec artifacts excluded from budget per `tasks.md` but remaining code delta still over. Chained PRs were not used. | Known, accepted. |
| W2 | **Socratic 3-level regression not re-run.** Manual Test 4 noted first assistant response already included the formula. Full Socratic-guidance regression is out of scope (archived `socratic-layer` change). | Follow-up logged. |
| W3 | **No automated smoke suite.** Only `tests/test_chat_sse_message_ids.py` is automated. Persistence, deletion, and history-injection scenarios rely on manual run file. | Follow-up. |
| W4 | Test-run file internal inconsistencies — **resolved** in re-verification. | ✅ Cleared. |

### Suggestions (carried over)

- S1: Adopt commit-per-task discipline more rigorously.
- S2: Add token-budget assertion for worst-case history window.
- S3: Promote ad-hoc smoke assertions into committed `tests/` scripts.
- S4: Re-run Socratic 3-level regression when `socratic-layer` prompts are updated.

---

## Known Follow-ups

1. **Socratic 3-level regression** — the archived `socratic-layer` change's prompts should be reviewed to ensure history injection does not unlock answer leakage or skip hint ladder rungs.
2. **Smoke test gap** — `generate_response` with non-empty history was structurally verified but never sent to Groq in a smoke test. Any future history work must include a real LLM round-trip.
3. **Promote ad-hoc tests** — the 9 API assertions from verify should become committed `tests/test_history_api.py` to continuously verify deletion, cross-student 403, and `HISTORY_WINDOW=0` behaviours.

---

## Source of Truth Updated

The following main specs now reflect the student-history behavior:

- `openspec/specs/student-identification/spec.md` — 120 lines, 7 requirements, 11 scenarios (NEW)
- `openspec/specs/conversation-persistence/spec.md` — 188 lines, 8 requirements, 14 scenarios (NEW)
- `openspec/specs/socratic-guidance/spec.md` — 231 lines, 11 requirements, 22 scenarios (MERGED — +1 requirement, +3 scenarios from delta)

---

## Commit Instructions (for the orchestrator)

The orchestrator stated they will handle commits. The working tree currently shows:

- **Deleted** (from `mv`): all files under `openspec/changes/student-history/`
- **Modified**: `openspec/specs/socratic-guidance/spec.md`
- **Untracked**: `openspec/changes/archive/2026-07-22-student-history/`, `openspec/specs/conversation-persistence/`, `openspec/specs/student-identification/`

No `git add` or `git commit` was executed by the archive sub-agent. The orchestrator should:

1. `git add` the archive directory, new specs, and modified socratic-guidance spec
2. `git rm` the old change directory files (or `git add -A` to stage both deletions and additions)
3. Commit with a message such as:
   ```
   docs(archive): archive student-history change and sync specs
   ```

---

## SDD Cycle Complete

The `student-history` change has been fully planned, explored, proposed, specified (3 delta specs), designed, implemented (6 tasks), verified (PASS WITH WARNINGS), re-verified, and archived. The change is now accessible in the archive as an audit trail.

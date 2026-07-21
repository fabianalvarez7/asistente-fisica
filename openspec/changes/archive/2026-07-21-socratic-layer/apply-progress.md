# Apply Progress: Socratic Layer

## Status

**partial**

Code changes (Tasks 1.1 and 1.2) and the regression query set (Task 1.3) are
complete. The 26-query validation run (Task 1.4) is deferred to the user because
the local environment lacks `GROQ_API_KEY` and the required Python dependencies.
Task 1.5 (final review gate) is complete.

## Branch

`feat/socratic-layer`

## Commits

| SHA | Message |
|-----|---------|
| `2f0eb10` | `feat(rag): wrap system prompt with Socratic instructions` |
| `c676c65` | `feat(rag): inject 3 few-shot examples for Socratic guidance` |
| `9c7cd63` | `test(socratic): define regression query set from last demo` |
| `d61f923` | `test(socratic): defer 26-query validation suite to user` |
>
> This progress report and the updated `tasks.md` are recorded in the final
> commit on `feat/socratic-layer`.

## Diff Summary

| File | Action | Δ lines |
|------|--------|---------|
| `rag/prompts/chat_prompt.py` | Modified | +17 / -3 |
| `rag/chain.py` | Modified | +56 / -0 |
| `tests/regression_queries.md` | Created | +69 / -0 |
| `tests/socratic_layer_run_2026-07-06.md` | Created | +82 / -0 |
| `openspec/changes/socratic-layer/apply-progress.md` | Created | +139 / -0 |
| `openspec/changes/socratic-layer/tasks.md` | Created | +69 / -0 |
| **Total** | | **+432 / -3** |

## Tasks Completed

- [x] **1.1** — Wrapped `SYSTEM_PROMPT` with Socratic instructions in
  `rag/prompts/chat_prompt.py`. Preserved RAG ground rules verbatim, kept the
  `{context}` placeholder, and encoded the 3-level hint ladder, "pista máxima",
  "señalar y repreguntar", voseo tone, and always-Spanish rule.
- [x] **1.2** — Added `_FEW_SHOT` constant in `rag/chain.py` with 3
  user/assistant pairs spanning error theory, kinematics, and dynamics. Injected
  the examples into the Groq call with `[system, *_FEW_SHOT, user_query]`.
  Streaming, threshold, model, and refusal behavior are unchanged.
- [x] **1.3** — Created `tests/regression_queries.md` with 8 regression queries
  covering in-corpus error theory, in-corpus exercise, off-topic,
  out-of-Física-1 physics, meta-question, polite greeting, LaTeX formula, and
  factual context-grounded answer.
- [ ] **1.4** — **Deferred to user.** The 26-query suite could not be executed
  locally because `GROQ_API_KEY` is not set and the `openai` package is not
  installed. A stub log was committed at
  `tests/socratic_layer_run_2026-07-06.md` with the full test plan and
  unblock instructions.
- [x] **1.5** — Final review gate completed.

## Test Results

- **File**: `tests/socratic_layer_run_2026-07-06.md`
- **Tests run**: 0 / 26
- **Pass / fail**: N/A (deferred)
- **Blocker**: missing `GROQ_API_KEY` and Python dependencies in the active
  environment.

## SHALL Coverage

| SHALL | Requirement | Covered by |
|-------|-------------|------------|
| #1 | Question-based Socratic guidance | Task 1.1 (hint ladder, guiding questions) |
| #2 | 3-level hint ladder ending at "pista máxima" | Task 1.1 |
| #3 | Error handling: "señalar y repreguntar" | Task 1.1 |
| #4 | Off-topic/out-of-scope refusal preserved | Task 1.1 (RAG rules kept verbatim) |
| #5 | RAG grounding preserved | Task 1.1 (RAG rules kept verbatim) |
| #6 | Rioplatense voseo tone | Task 1.1 |
| #7 | Single-turn behavior enforced | Task 1.1 (no history changes) |
| #8 | LaTeX formulas preserved | Task 1.1 (RAG rules kept verbatim) |
| #9 | Few-shot examples: ≥3 pairs, topic-agnostic, voseo | Task 1.2 |
| #10 | Pista máxima bounded to principle/general formula | Task 1.1 |

## Deviations from Plan

1. **Task 1.4 commit message**: The task artifact prescribed
   `test(socratic): run 26-query validation suite against spec`. Because no
   tests were actually run, the commit message was changed to
   `test(socratic): defer 26-query validation suite to user` to avoid a
   misleading history entry.
2. **Task 1.4 completion status**: Marked as deferred rather than complete, as
   instructed in the task description.
3. **Task 1.1 line count**: The implementation added +17/-3 lines instead of
   the estimated +25/-1. The prompt is more concise than the estimate while
   still covering all SHALL requirements.
4. **No `rag/prompts/__init__.py` change**: The few-shot list lives in
   `chain.py`, so no export change was needed. This matches design.md's
   recommendation.

## Blockers

- The user must run the 26-query validation suite manually after configuring the
  environment:
  1. `pip install -r requirements.txt`
  2. Set `GROQ_API_KEY` in `.env`
  3. Ensure `data/chroma/` is indexed (run `python scripts/indexar_pdfs.py` if
     needed)
  4. Execute the queries and record results in
     `tests/socratic_layer_run_2026-07-06.md` or a new dated file.

## Rollback Confirmation

Rolling back the functional change requires reverting only the two code
commits:

```bash
git revert 2f0eb10
git revert c676c65
```

No database migration, no model swap, no embedding re-bake, no frontend or
infrastructure changes are required.

## Out-of-Scope Check

No changes were made to:

- `app/main.py` or `app/static/`
- `dashboard/`
- `rag/retrievers/`, `rag/loaders/`, `rag/splitters/`
- `requirements.txt`
- Model, embedding model, or ChromaDB index
- Cosine distance threshold (`0.5`) or chain-level refusal
- Conversation history / student identification

## Next Recommended

`verify` — run `sdd-verify` against the spec once the user has executed the
26-query validation suite.

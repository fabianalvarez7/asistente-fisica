# Tasks: Socratic Layer

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~45 (code) + ~100 (test docs) = ~145 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Socratic prompt + few-shot + test run | PR 1 | Single PR; code ~45 lines, well under 400-line budget |

## Phase 1: Prompt Engineering

- [x] **1.1** Prepend Socratic instructions block to `SYSTEM_PROMPT` in `rag/prompts/chat_prompt.py`
  - Update docstring line 3 (remove "intentionally NOT Socratic")
  - Add Socratic block BEFORE RAG ground rules: guide role, 3-level hint ladder, "dame la respuesta" → pista máxima, "señalar y repreguntar", voseo tone, always-Spanish, single-turn
  - Keep RAG ground rules (lines 10-17) and `{context}` placeholder verbatim
  - **SHALLs**: #1, #2, #3, #4, #5, #6, #7, #8, #10
  - **Depends on**: none
  - **Est. diff**: `chat_prompt.py` +25/-1
  - **Commit**: `feat(rag): wrap system prompt with Socratic instructions`

- [x] **1.2** Inject 3 few-shot examples into Groq call in `rag/chain.py`
  - Define `_FEW_SHOT` constant: 3 user/assistant pairs (error theory, kinematics, dynamics) in voseo, no numerical answers, ending with guiding questions
  - Inject into messages: `[system] + _FEW_SHOT + [user_query]`
  - **SHALLs**: #6, #9
  - **Depends on**: 1.1
  - **Est. diff**: `chain.py` +12/-3
  - **Commit**: `feat(rag): inject 3 few-shot examples for Socratic guidance`

## Phase 2: Validation

- [x] **1.3** Define regression query set in `tests/regression_queries.md`
  - 8 queries: in-corpus concept, in-corpus exercise, off-topic, out-of-scope, meta-question, LaTeX formula, greeting, out-of-Física-1 physics. Each with expected behavior.
  - **SHALLs**: #4, #5, #8
  - **Depends on**: none
  - **Est. diff**: `tests/regression_queries.md` +35 (new file)
  - **Commit**: `test(socratic): define regression query set`

- [ ] **1.4** Run 26-query validation suite and log results
  - 10 Socratic + 8 regression + 8 edge cases (per design.md test plan)
  - Log query, verbatim response, pass/fail in `tests/socratic_layer_run_<date>.md`
  - On failure: iterate prompt (Task 1.1, +5-10 lines max), re-run
  - **SHALLs**: all 10
  - **Depends on**: 1.1, 1.2, 1.3
  - **Est. diff**: test log +70 (new file); possible `chat_prompt.py` +5
  - **Commit**: `test(socratic): run 26-query validation suite against spec`

## Phase 3: Review Gate

- [x] **1.5** Final review: confirm change matches proposal, spec, and design
  - Verify rollback: `git revert` of Tasks 1.1 and 1.2 is sufficient
  - Confirm no out-of-scope changes
  - **Depends on**: 1.4
  - **Est. diff**: 0
  - **Commit**: none (review only)

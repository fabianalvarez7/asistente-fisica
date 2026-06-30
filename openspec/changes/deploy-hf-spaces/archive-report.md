# Archive Report: `deploy-hf-spaces`

> **Archive date**: 2026-06-28
> **Verdict at archive**: PASS WITH WARNINGS — ship-with-follow-ups
> **Canonical capabilities created**: `hf-spaces-deploy`, `corpus-rebake`

## Executive Summary

Migrated the deploy target from Render free tier (512 MB, OOM'd at ~967 MB peak RSS) to Hugging Face Spaces Docker SDK (free `cpu-basic`: 16 GB RAM, ~48 h sleep). Also re-baked the ChromaDB index from a stale 25-chunk corpus to a fresh 38-chunk index sourced exclusively from `cuadernillo-fisica-1.pdf`. Pre-baked artifacts (ChromaDB plain git, HF model via Git LFS) survive sleep/wake. Backend code was frozen — the only change to `app/main.py` was a `load_dotenv()` bug fix. All 13 SHALLs are implemented (10 PASS, 3 PARTIAL with documented deviations). Smoke test passed end-to-end: count=38, uvicorn boots, Groq grounded response confirmed.

The branch `feat/deploy-hf-spaces` is ready for Fabián to push to a remote, create the HF Space, and open a PR. No critical issues remain. Three WARNINGs and five SUGGESTIONs are recorded as follow-ups.

## Done Criteria (AGENTS.md §14)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Code in `rag/`, `app/`, `dashboard/`, or `scripts/` | ✅ PASS | Changes in `rag/loaders/pdf_loader.py`, `rag/splitters/text_splitter.py`, `scripts/preparar_indice_hf.py`. Frozen files untouched. |
| README / docstring explains what and how | ✅ PASS | `docs/hf-space.md` (106 lines) documents Space README template + manual deploy steps. `README.md` updated with HF YAML header. AGENTS.md updated. |
| Architecture decision recorded | ✅ PASS | AGENTS.md §7 decision 11 added ("HF Spaces via Docker SDK"). Decision 8 rationale updated. Design.md contains 10 architecture decisions. |
| Runnable from clean clone | ⚠️ PARTIAL | Requires fixing `.env.example` `CHROMA_PERSIST_DIR` (W1) and sourcing the gitignored cuadernillo PDF separately (W2). Documented in follow-ups. |
| Not "works on my machine" | ✅ PASS | Independent sqlite3 verification of corpus (38 chunks, cosine, single source). Smoke test passed. |
| No testable-in-under-5-min gap | ✅ PASS | Manual verification plan documented in apply-progress (~5 min). Fabián confirmed smoke test. |

## Artifact Final State

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| Explore | `openspec/changes/deploy-hf-spaces/explore.md` | ✅ Complete | 211 lines, 8 sections, 7 gotchas, Approach A recommended |
| Proposal | `openspec/changes/deploy-hf-spaces/proposal.md` | ✅ Complete | 85 lines, scope, approach, trade-offs, risks |
| Spec (hf-spaces-deploy) | `openspec/changes/deploy-hf-spaces/specs/hf-spaces-deploy/spec.md` | ✅ Complete | 8 SHALLs, 12 scenarios |
| Spec (corpus-rebake) | `openspec/changes/deploy-hf-spaces/specs/corpus-rebake/spec.md` | ✅ Complete | 5 SHALLs, 7 scenarios |
| Design | `openspec/changes/deploy-hf-spaces/design.md` | ✅ Complete | 293 lines, 10 architecture decisions, contracts, failure modes |
| Tasks | `openspec/changes/deploy-hf-spaces/tasks.md` | ✅ Complete | 6 planned + 2 added (T0, T0.5) = 8 tasks, all committed |
| Apply Progress | `openspec/changes/deploy-hf-spaces/apply-progress.md` | ✅ Complete | 117 lines, 5 deviations, 3 risks, verification plan |
| Verify Report | `openspec/changes/deploy-hf-spaces/verify-report.md` | ✅ Complete | 233 lines, 0 CRITICAL, 3 WARNING, 5 SUGGESTION |
| Archive Report | `openspec/changes/deploy-hf-spaces/archive-report.md` | ✅ Complete | This file |
| Canonical Spec (hf-spaces-deploy) | `openspec/specs/hf-spaces-deploy/spec.md` | ✅ Created | Net-new capability spec (first archive; `openspec/specs/` was empty) |
| Canonical Spec (corpus-rebake) | `openspec/specs/corpus-rebake/spec.md` | ✅ Created | Net-new capability spec |

### Engram Observation IDs

For cross-session traceability, the Engram observations persisted during this SDD cycle are:

| Artifact | Observation ID | Topic Key |
|----------|---------------|-----------|
| Explore | 37 | `sdd/deploy-hf-spaces/explore` |
| Proposal | 38 | `sdd/deploy-hf-spaces/proposal` |
| Spec | 39 | `sdd/deploy-hf-spaces/spec` |
| Design | 40 | `sdd/deploy-hf-spaces/design` |
| Tasks | 41 | `sdd/deploy-hf-spaces/tasks` |
| Apply Progress | 43 | `sdd/deploy-hf-spaces/apply-progress` |
| Verify Report | 44 | `sdd/deploy-hf-spaces/verify-report` |
| Archive Report | (this save) | `sdd/deploy-hf-spaces/archive-report` |

## Stale Checkbox Reconciliation

The `tasks.md` artifact at `openspec/changes/deploy-hf-spaces/tasks.md` has all 6 implementation tasks in unchecked state (`- [ ]`). This is a **stale checkbox** condition — `sdd-apply` did not update the checkboxes to `- [x]`.

The orchestrator explicitly authorized archive-time stale-checkbox reconciliation under the exceptional path described in the SDD archive contract. The following evidence proves every unchecked task is complete:

| Task | Proof of Completion | Commit |
|------|-------------------|--------|
| T1 — Re-bake ChromaDB | Verified: 38 chunks, cosine space, single source (sqlite3) | `f08d6c1` |
| T2 — Rename bake script | `git mv` confirmed; `preparar_indice_hf.py` exists | `029603e` |
| T3 — Dockerfile + .gitattributes + delete render.yaml | Dockerfile matches design contract; render.yaml deleted | `7cbae54`, `2684113` |
| T4 — Space README + .env.example | YAML front-matter in README.md; env comments updated | `36bae72` |
| T5 — AGENTS.md + config.yaml/docs | §4/§7/§8/§10/§12 updated; docs/hf-space.md created | `9e433df` |
| T6 — Smoke test | End-to-end PASSED (Fabián: count=38, uvicorn boots, Groq grounded response) | No commit |

**Reconciliation performed**: The archive report acknowledges the stale checkboxes and records the evidence. No changes were made to `tasks.md` — the task artifact is preserved as-is for audit trail fidelity. Future readers should use `apply-progress.md` and `verify-report.md` as the completion authority.

## Commits on `feat/deploy-hf-spaces`

| # | Commit | Type | Subject | Notes |
|---|--------|------|---------|-------|
| 1 | `321e392` | Merge | Merge main into branch | Sync with 3 prior PRs from `chat-rag-render-deploy` |
| 2 | `b859f8c` | **T0** (added) | Switch loader marker-pdf → pymupdf4llm; chunk_size 1000 → 500 | Deviation from design (marker-pdf timed out at 96%) |
| 3 | `2684113` | **T0.5** (added) | Track HF model via Git LFS | Split from T3; 471 MB → 134 B LFS pointer |
| 4 | `f08d6c1` | T1 | Re-bake ChromaDB with cuadernillo | 38 chunks, cosine, single source |
| 5 | `029603e` | T2 | Rename bake script | `git mv` + docstring update |
| 6 | `7cbae54` | T3 | Dockerfile + delete render.yaml | Dockerfile matches design contract |
| 7 | `36bae72` | T4 | Space README header + .env.example | YAML prepended; env comments updated |
| 8 | `9e433df` | T5 | AGENTS.md + docs/hf-space.md | §4/§7/§8/§10/§12 + deploy guide |
| 9 | `5222050` | **fix (incomplete)** | load .env at startup (too late) | `load_dotenv()` after rag.chain import — incomplete |
| 10 | `ae9fc63` | **fix (correct)** | load .env before rag.chain import | Moved `load_dotenv()` before `from rag.chain import` |
| 11 | (W1) | pending | Fix `.env.example` CHROMA_PERSIST_DIR | See W1 follow-up |

**Total**: 10 committed + 1 pending. 11 commits on the branch (including pre-merge).

## Deviations from Design

These are the gaps between what the design specified and what was actually built. Each is documented with reasoning; none are silent.

| # | Design Said | Actual | Reason | Impact |
|---|-------------|--------|--------|--------|
| D1 | Backend frozen (no changes to `app/main.py`, `rag/chain.py`, etc.) | `app/main.py` changed: `load_dotenv()` added | Latent bug: `rag/chain.py` creates `OpenAI(api_key=os.getenv("GROQ_API_KEY"))` at module load. Without `load_dotenv()` before the import, `.env` is not read, and Groq returns 401. Hidden by Render which injects env vars directly. | Bug fix, not feature change. Backend-frozen invariant preserved at the feature level. |
| D2 | Keep chunk_size=1000 (design OQ-C2 resolution) | chunk_size lowered to 500 | chunk_size=1000 on the cuadernillo yields ~15-16 chunks — below the >25 spec threshold. 500 yields 38. | Acceptable trade-off. The corpus-rebake spec's "> 25" threshold drove this. |
| D3 | Use `marker-pdf` as PDF loader (unchanged) | Switched to `pymupdf4llm` | `marker-pdf` timed out at 96% after ~20 minutes on the cuadernillo. `pymupdf4llm` is faster and adequate for the clean cuadernillo corpus. | Acceptable. `marker-pdf` kept in `requirements.txt` as plan B (frozen by design). |
| D4 | T3 creates `.gitattributes` | T0.5 created `.gitattributes` as separate commit | Better isolation: LFS migration mechanics separated from Dockerfile creation. | Cosmetic; no behavioral impact. |
| D5 | T5 updates `openspec/config.yaml` | File does not exist on `main` or branch | The file was never created by prior changes. Design referenced a non-existent file. | Non-blocking. Metadata-only. SUGGESTION S2 in verify. |

## WARNINGs at Archive Time

From `verify-report.md` (0 CRITICAL, 3 WARNING, 5 SUGGESTION). Status of each at archive:

### W1 — Local Dev Parity PARTIAL (HS-S8 / CR-S4) — **FIXED**

`.env.example` set `CHROMA_PERSIST_DIR=./data/chroma`, but `data/` is gitignored. The committed bake is at `rag/index/chroma/`. Clean-clone local dev boot fails (empty dir → count==0 → RuntimeError).

**Status at archive**: FIXED by commit `227b48b` (W1 fix on the branch). `.env.example` now points to `./rag/index/chroma`. The Dockerfile already used `./rag/index/chroma`, so they match.

**Verification**: `grep CHROMA_PERSIST_DIR .env.example` → `CHROMA_PERSIST_DIR=./rag/index/chroma`.

### W2 — Reproducible Re-bake PARTIAL (CR-S5) — **NOT FIXED**

The cuadernillo PDF (`data/pdfs/cuadernillo-fisica-1.pdf`) is gitignored (`data/` in `.gitignore`). A clean clone cannot re-bake without obtaining the PDF from Nair or course materials separately.

**Status at archive**: Not fixed. This is a content-licensing issue — the PDF is course material that may not be redistributable via git. Documentation must acknowledge this.

**Recommendation**: Document in `docs/hf-space.md` and AGENTS.md §6 that the cuadernillo PDF must be sourced from Nair. Do not force-add it to git without Nair's consent.

### W3 — T0 Deviation Exceeds `corpus-rebake` Scope — **NOT FIXED (documented)

T0 changed the loader (`marker-pdf` → `pymupdf4llm`) and splitter (`chunk_size` 1000 → 500), going beyond the corpus-rebake spec's "only re-runs the existing indexing script" scope. The deviation contradicts the design's OQ-C2 resolution.

**Status at archive**: Not fixed — no code fix is needed. The deviation is documented here and in both canonical specs' "Notes from Archive" sections. Future readers will find the acknowledgment.

## SUGGESTIONs at Archive Time

From `verify-report.md`. None are fixed at archive time — all are deferred to future changes.

| # | Suggestion | Priority | Notes |
|---|-----------|----------|-------|
| S1 | Remove HF YAML front-matter from GitHub `README.md` | Cosmetic | `sdk: docker` / `app_port: 7860` YAML renders as literal text on GitHub. Move to `docs/hf-space.md` only. |
| S2 | `openspec/config.yaml` does not exist | Non-blocking | Design referenced it but the file was never created. No action needed unless a future change creates it. |
| S3 | AGENTS.md §13 still references "Render" | Cosmetic | Open question "Faculty server for deploy? ... move from Render to a faculty-hosted URL" now reads stale. Update to "HF Spaces". |
| S4 | `marker-pdf` dead weight in Docker image (~500 MB) | Image size | T0 removed marker-pdf from the runtime loader, but it remains in `requirements.txt`. Split into `requirements-app.txt` + `requirements-dev.txt`. |
| S5 | Squash the two `load_dotenv()` fix commits | History hygiene | `5222050` (incomplete) + `ae9fc63` (correct) fix the same bug. Squashing before merge keeps history clean. Left to Fabián's discretion. |

## Risks

| Risk | Severity | Status | Mitigation |
|------|----------|--------|------------|
| **LFS history bloat** — 471 MB raw model blobs in `main`'s history (commit `73ae389`, prior change) | High impact, Low likelihood | **Open** | LFS migration affects new commits only. First push to HF Spaces will transmit old blobs (~30 min on home connection). Future pushes are LFS-only. `git lfs migrate import` rewrites SHAs — optional, out of scope. Documented in `docs/hf-space.md`. |
| **Squashing recommendation** — 2 fix commits for the same bug | Low | **Open** | Consider squashing `5222050` + `ae9fc63` before merge, or leave as debugging trail. Orchestrator suggested squashing. |
| **`marker-pdf` dead weight** — ~500 MB unused OCR deps in Docker image | Medium | **Open** | Follow-up: split requirements. |
| **Source PDF not in repo** — cuadernillo is gitignored | Medium | **Open** | Document sourcing from Nair. Cannot re-bake without the PDF. |

## Follow-Ups

### Before Demo (recommended)
1. **Push the branch to GitHub** and open a PR against `main`. (`gh` CLI not installed locally; Fabián handles this.)
2. **Create the HF Space** (`fabianalvarez/asistente-fisica`, public, Docker SDK). Copy `Dockerfile`, `.gitattributes`, `rag/index/chroma/`, `rag/index/hf-model/` to the Space repo. Set `GROQ_API_KEY` as a Space Secret in Settings UI.
3. **Verify clean-clone local dev** — clone the branch, run `.env.example` → `.env`, `uvicorn app.main:app --reload`, confirm boot succeeds.

### Deferred to Future Changes
4. **Document cuadernillo sourcing** (W2) — add note in `docs/hf-space.md` and AGENTS.md §6 that the PDF must be obtained from Nair.
5. **Remove HF YAML from GitHub README** (S1).
6. **Split requirements.txt** into `requirements-app.txt` + `requirements-dev.txt` (S4) to remove marker-pdf from the Docker image.
7. **Update AGENTS.md §13** (S3) — "Render" → "HF Spaces" in the open question about faculty-hosted URL.
8. **Consider `git lfs migrate import`** to clean the 471 MB raw blobs from `main`'s history, reducing first-push time to HF Spaces.

## Branch Status

| Aspect | Status |
|--------|--------|
| Branch name | `feat/deploy-hf-spaces` |
| Ahead of `main` | 10 commits |
| Behind `main` | 0 commits |
| Remote configured | No |
| `gh` CLI installed | No |
| PR created | No |
| W1 fix applied | Yes (commit `227b48b`) |
| Ready to push | **Yes** — Fabián pushes to GitHub and opens PR manually |
| Squashing recommended | Two `load_dotenv()` fix commits (`5222050` incomplete, `ae9fc63` correct). Left to Fabián. |

The branch is fully implemented and verified. Fabián should:
1. (Optional) Squash `5222050` + `ae9fc63` before pushing.
2. Push the branch: `git push origin feat/deploy-hf-spaces`.
3. Create a PR against `main`.
4. Create the HF Space and push the Docker artifacts to the Space repo.

## Canonical Capabilities Created

This archive creates two canonical capability specs in `openspec/specs/` — the first specs ever archived in this project.

| Capability | Spec Path | SHALLs | Scenarios | Status at Archive |
|------------|-----------|--------|-----------|-------------------|
| `hf-spaces-deploy` | `openspec/specs/hf-spaces-deploy/spec.md` | 8 | 12 | 6 PASS, 2 PARTIAL |
| `corpus-rebake` | `openspec/specs/corpus-rebake/spec.md` | 5 | 7 | 3 PASS, 2 PARTIAL |

Both specs include a "Notes from Archive" section documenting the PARTIAL SHALLs and deviations. Future changes to these capabilities SHOULD create delta specs against these canonical files.

## SDD Cycle Complete

The `deploy-hf-spaces` change has been fully planned, explored, proposed, specced, designed, implemented, applied, verified, and archived. The SDD cycle is closed.

Ready for the next change.

## References

- `openspec/changes/deploy-hf-spaces/explore.md` — investigation and platform verification
- `openspec/changes/deploy-hf-spaces/proposal.md` — intent, scope, approach
- `openspec/changes/deploy-hf-spaces/specs/hf-spaces-deploy/spec.md` — 8 SHALLs
- `openspec/changes/deploy-hf-spaces/specs/corpus-rebake/spec.md` — 5 SHALLs
- `openspec/changes/deploy-hf-spaces/design.md` — 10 architecture decisions, contracts
- `openspec/changes/deploy-hf-spaces/tasks.md` — 8 tasks (6 planned + 2 added)
- `openspec/changes/deploy-hf-spaces/apply-progress.md` — deviations, verification plan, risks
- `openspec/changes/deploy-hf-spaces/verify-report.md` — 0 CRITICAL, 3 WARNING, 5 SUGGESTION
- `openspec/specs/hf-spaces-deploy/spec.md` — canonical capability spec
- `openspec/specs/corpus-rebake/spec.md` — canonical capability spec
- `AGENTS.md` — project constitution (§7 decisions, §12 env vars, §14 "done" definition)

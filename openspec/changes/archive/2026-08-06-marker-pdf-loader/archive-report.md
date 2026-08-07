# Archive Report: marker-pdf-loader

**Change**: marker-pdf-loader
**Archived**: 2026-08-06
**Archive path**: `openspec/changes/archive/2026-08-06-marker-pdf-loader/`
**Artifact store mode**: openspec
**Branch**: `main` (single branch workflow for prototype)
**Verdict**: PASS-WITH-WARNINGS (no CRITICAL, 6 WARNINGs all non-blocking)

---

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| corpus-rebake | **Updated** (merged delta) | Single-Corpus Source (1→5 PDFs + formulas.md), Reproducible Re-bake Workflow (pymupdf4llm→marker-pdf + scripts/verify_latex.py), 7 ADDED requirements (REQ-1 to REQ-7), 3 NFR (≥2000 LaTeX, smoke test pass, no pymupdf4llm) |

### Merge details for `openspec/specs/corpus-rebake/spec.md`

**MODIFIED** — `Single-Corpus Source` (replaced entirely):
- Before: "exactly one source PDF: `data/pdfs/cuadernillo-fisica-1.pdf`. No other PDFs SHALL be present in `data/pdfs/` during the bake."
- After: "exactly 5 canonical PDFs in `data/pdfs/`: `Cinemática 1.pdf`, `Cinemática 2.pdf`, `Dinámica 1.pdf`, `Dinámica 2pdf.pdf`, `cuadernillo-fisica-1.pdf`. Optional `formulas.md` may also be present. The canonicity gate in `scripts/indexar_pdfs.py` enforces this list before indexing, raising `FileNotFoundError` with the missing list if any are absent."

**MODIFIED** — `Stale Index Replacement` (count updated):
- Before: "> 25" chunks
- After: "= 1374" chunks (1360 from 5 PDFs + 14 from formulas.md)

**MODIFIED** — `Reproducible Re-bake Workflow` (expanded):
- Before: single documented command against `cuadernillo-fisica-1.pdf`
- After: two-step — `python scripts/indexar_pdfs.py --reset` to re-bake, then `python scripts/verify_latex.py` to assert NFR ≥2000 LaTeX. Workflow documented in `docs/hf-space.md`. The bake takes 5-7h on Mac MPS (single `Recognizing Text` pass alone can take 1-2h per chapter). Models are baked at Docker build time; no network access required at runtime.

**MODIFIED** — `Committed Baked Artifact` (size updated):
- Before: implicit "small enough to commit"
- After: "12 MB on disk, well under 100 MB Git-LFS cap. Contains `chroma.sqlite3` + UUID dir."

**ADDED** — 7 new requirements appended after existing requirements, before "## Notes from Archive":
- REQ-1: PDF loader SHALL use `marker-pdf` (1.10.2+) instead of `pymupdf4llm`
- REQ-2: `scripts/indexar_pdfs.py` SHALL enforce a 5-PDF canonicity gate before indexing
- REQ-3: Re-bake workflow SHALL be reproducible from a clean clone with documented commands
- REQ-4: The `PdfConverter` SHALL be a module-level singleton (`_CONVERTER`) with lazy init
- REQ-5: The smoke test suite SHALL include a `test_formula_retrieval()` assertion that verifies a formula query returns chunks containing LaTeX
- REQ-6: `Dockerfile` SHALL pre-bake marker-pdf models at build time via `RUN python -c "from marker.models import create_model_dict; create_model_dict()"` with `MODEL_CACHE_DIR=/app/rag/index/marker-models`
- REQ-7: A `scripts/verify_latex.py` script SHALL exist and assert that the baked ChromaDB has ≥2000 LaTeX occurrences across the indexed corpus

**ADDED** — 3 NFRs:
- NFR-1: The baked index SHALL have ≥2000 LaTeX occurrences (display + inline) across the 5 canonical PDFs (observed: 2665)
- NFR-2: The smoke test suite SHALL pass on a fresh re-bake (formula retrieval assertion PASS for all formula queries)
- NFR-3: `pymupdf4llm` SHALL NOT appear in `requirements.txt` or any project `.py` file (only the dev `.venv/` may retain the installed package as a harmless leftover)

**MODIFIED** — `## Notes from Archive` (replaced):
- Before: archived note from `deploy-hf-spaces` change (2026-06-28)
- After: "This spec was updated by the `marker-pdf-loader` change (2026-08-06). The 5-PDF canonical corpus and marker-pdf loader replaced the 1-PDF cuadernillo-only + pymupdf4llm setup. Re-bake yields 1374 chunks; NFR ≥2000 LaTeX (observed 2665). Verdict: PASS-WITH-WARNINGS (6 non-blocking WARNINGs reconciled in `design.md` and `verify-report.md`)."

**MODIFIED** — Header (replaced):
- Before: "Archived capability spec — persisted from the `deploy-hf-spaces` change on `2026-06-28`."
- After: "Updated capability spec — last updated by the `marker-pdf-loader` change on `2026-08-06`. Source: `openspec/changes/archive/2026-08-06-marker-pdf-loader/specs/corpus-rebake/spec.md`. Future changes SHOULD create a delta spec against this file."

---

## Archive Contents

| Artifact | Status |
|----------|--------|
| `proposal.md` | ✅ Present |
| `specs/corpus-rebake/spec.md` | ✅ Present (delta spec) |
| `design.md` | ✅ Present (includes "## Implementation Reconciliation" section) |
| `tasks.md` | ✅ Present (15/15 tasks complete) |
| `apply-progress.md` | ✅ Present (3-batch strategy, 9 work-unit commits) |
| `verify-report.md` | ✅ Present (PASS-WITH-WARNINGS) |
| `archive-report.md` | ✅ Present (this file) |

---

## Commits in main (9 work-unit commits, oldest first)

| # | SHA | Commit message | Scope |
|---|-----|---------------|-------|
| 1 | `1e3785f` | `feat(rag): swap pymupdf4llm for marker-pdf singleton` | `rag/loaders/pdf_loader.py` (REQs 1, 4) |
| 2 | `c145805` | `chore(deps): uncomment marker-pdf>=1.10 and drop pymupdf4llm` | `requirements.txt` (REQ-2, NFR-3) |
| 3 | `d876021` | `feat(scripts): add canonicity gate for 5-PDF corpus in indexar_pdfs.py` | `scripts/indexar_pdfs.py` (REQ-2) |
| 4 | `8b3d6c3` | `feat(scripts): add verify_latex.py to assert NFR ≥2000 LaTeX occurrences` | `scripts/verify_latex.py` (REQ-7, NFR-1) |
| 5 | `42eef80` | `feat(deploy): bake marker-pdf surya models into Docker image` | `Dockerfile` (REQ-6) |
| 6 | `eb5131d` | `docs(scripts): clarify corpus + model bake notes in preparar_indice_hf.py` | `scripts/preparar_indice_hf.py` (doc) |
| 7 | `5afd167` | `docs(hf-space): update re-bake section for marker-pdf 5-PDF pipeline` | `docs/hf-space.md` (REQ-3) |
| 8 | `ad96f9c` | `feat(scripts): add formula retrieval smoke test for marker-pdf LaTeX output` | `scripts/run_socratic_tests.py` (REQ-5) |
| 9 | `2e692be` | `chore(deploy): re-bake ChromaDB with marker-pdf (1374 chunks, 5 PDFs + formulas.md)` | `rag/index/chroma/` (12 MB, NFR-1) |

Plus the archive commit (this phase) at HEAD.

---

## Design reconciliations

See `design.md` "## Implementation Reconciliation" section for full details. Summary:

1. **Re-bake time**: 3.5–4.2h (design) → 5–7h observed. Estimate was based on a 43-min benchmark on one chapter; actual sub-block count was ~3x higher.
2. **OQ-2 reversed**: KEEP pymupdf4llm (design) → REMOVE entirely (applied). Spec left open; task 1.2 chose removal.
3. **OQ-3 reversed**: `--check-latex` flag (design) → sibling `scripts/verify_latex.py` (applied). Cleaner separation of concerns.
4. **Env var name correction**: `SURYA_MODEL_CACHE_DIR` (design) → `MODEL_CACHE_DIR` (verified against surya-ocr 0.11.8). Old name would have caused ~3 GB re-download per cold start.
5. **`ensure_marker_models()` removed**: design proposed adding this to `preparar_indice_hf.py`; applied approach bakes models directly in Dockerfile RUN step. Functionally equivalent, fewer moving parts.

Two non-blocking softness gaps documented as W-3 (per-chapter ≥400 not enforced) and W-4 (formula-retrieval assertion is non-fatal). Both are future enhancements, not regressions.

---

## Warnings (non-blocking, post-archive)

- **W-3** (follow-up): Add per-chapter ≥400 floor to `verify_latex.py` (~6 lines). Current data passes; prevents silent regressions.
- **W-4** (follow-up): Make `test_formula_retrieval()` fatal (`sys.exit(1)` on FAIL) for future CI use. Currently non-fatal because smoke run is a manual review tool.
- **S-1** (post-deploy): Measure cold-start timing on real HF Space (PERF-1 spec requirement). Record in `docs/hf-space.md`.

---

## Engram observation IDs

- `#172` — `marker-pdf-loader/apply-strategy`: 3-batch apply strategy
- `#173` — `sdd-preflight/marker-pdf-loader-2026-08-06`: preflight decisions
- `#177` — `marker-pdf-loader/env-var-correction`: `MODEL_CACHE_DIR` fix
- `#178` — `sdd/marker-pdf-loader/apply-progress`: apply progress (latest)
- `#179` — `marker-pdf-loader/rebake-result`: 1374 chunks, 0 errors
- `#181` — `sdd/marker-pdf-loader/verify-findings`: verify findings (PASS-WITH-WARNINGS)
- `#182` — `marker-pdf-loader/design-reconciliation`: design.md "## Implementation Reconciliation" section
- `#183+` — this archive report

---

## Next steps for user

1. **Push and open a PR**:
   ```bash
   git push -u origin main
   gh pr create --base main --title "feat(rag): swap pymupdf4llm for marker-pdf (5-PDF corpus, ≥2000 LaTeX NFR)" --body "See openspec/changes/archive/2026-08-06-marker-pdf-loader/archive-report.md for full details. Closes the marker-pdf-loader SDD change (PASS-WITH-WARNINGS, 9 work-unit commits, 1374 chunks, 2665 LaTeX delimiters, 0 pymupdf4llm references)."
   ```
2. **After PR is merged**, deploy the new Docker image to HF Spaces. The image needs to re-build to bake the marker-pdf models, then push.
3. **Measure cold-start timing** (PERF-1): time the first `/chat` request after Space sleep. Record in `docs/hf-space.md`.
4. **(Optional, non-blocking)** W-3 and W-4 follow-ups.

---

## Relevant files

- **Archived change**: `openspec/changes/archive/2026-08-06-marker-pdf-loader/`
  - `proposal.md`, `specs/corpus-rebake/spec.md`, `design.md`, `tasks.md`
  - `apply-progress.md`, `verify-report.md`, `archive-report.md`
- **Canonical spec (updated)**: `openspec/specs/corpus-rebake/spec.md`
- **All 9 work-unit commits** in `main` (oldest: `1e3785f`, newest: `2e692be`)
- **Plus the archive commit** at HEAD

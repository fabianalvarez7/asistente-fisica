# Verify Report: marker-pdf-loader

**Change**: marker-pdf-loader
**Verifier**: fresh-context `sdd-verify` sub-agent
**Date**: 2026-08-07
**Verdict**: PASS-WITH-WARNINGS

## Summary

All 7 REQ + 3 NFR pass with measured runtime evidence. No CRITICAL findings. 6 WARNINGs (all non-blocking design-vs-impl drifts and minor assertion-strength gaps) and 2 SUGGESTIONs (cold-start perf measurement, openspec commit timing).

## CRITICAL findings

(none)

## WARNING findings

- **W-1** — `pymupdf4llm` removed from requirements.txt; design.md OQ-2 said KEEP. Spec REQ-2 explicitly leaves this open; tasks 1.2 directs removal; verify acceptance NFR-3 requires removal. → Reconciled in design.md "## Implementation Reconciliation" (Section 2: OQ-2 reversal).
- **W-2** — `scripts/verify_latex.py` is a sibling script, not the `--check-latex` flag inside `indexar_pdfs.py`. Spec OQ-3 lists sibling as valid; tasks 2.2 directs the sibling. → Reconciled in design.md (Section 3: OQ-3 reversal).
- **W-3** — `verify_latex.py` asserts total ≥2000 only; does NOT enforce per-chapter ≥400. Current data passes both (Cinemática1=577, Cinemática2=832, Dinámica1=417, Dinámica2=748). A regression where one chapter drops to 0 while total stays ≥2000 would slip past the script. → Follow-up: 6-line change to add `min_per_pdf` argument. Non-blocking.
- **W-4** — `run_socratic_tests.py` formula-retrieval assertion is "non-fatal" (no `sys.exit(1)`). Spec REQ-6 only requires the assertion "inspects retrieved context" and "reports PASS" — so spec-compliant. Design's hard-gate intent was softened for prototype UX. → Follow-up: change result to `sys.exit(1)` in `__main__` for future CI use. Non-blocking.
- **W-5** — `openspec/changes/marker-pdf-loader/` was UNTRACKED in git at verify time. → Resolved at archive (folder moved to `openspec/changes/archive/2026-08-06-marker-pdf-loader/` via `git mv`).
- **W-6** — `design.md` prose re-bake time (3.5–4.2h) and `ensure_marker_models()` proposal are stale vs shipped reality. → Reconciled in design.md "## Implementation Reconciliation" (Sections 1 and 5: estimate update + simplification).

## SUGGESTION findings

- **S-1** — PERF-1 cold-start budget not measured. `docs/hf-space.md:98` states the budget (20–40s) without a measured number. PERF-1 can only be measured post-deploy on the real HF Space. → User should measure after first deploy and record in `docs/hf-space.md`.
- **S-2** — Commit the openspec artifacts together with the archive. → Done (W-5 resolution).

## Spec compliance (7 REQ + 3 NFR)

- **REQ-1** (loader swap to marker-pdf): **PASS** — `rag/loaders/pdf_loader.py:15-16` imports `from marker.converters.pdf import PdfConverter`; `pymupdf4llm` not imported anywhere.
- **REQ-2** (single-corpus source, 5 PDFs): **PASS** — `scripts/indexar_pdfs.py:31-49` defines `CANONICAL_PDFS` (5 names) + `_check_canonical_corpus()` which `sys.exit(1)`s with missing list; gated in `main()` at line 219-220.
- **REQ-3** (reproducible re-bake workflow): **PASS** — `docs/hf-space.md:80-94` documents `indexar_pdfs.py --reset` → `verify_latex.py` → `cp` → `git commit`; `preparar_indice_hf.py:16-28` docstring documents dev/deploy workflow.
- **REQ-4** (singleton converter, lazy init): **PASS** — `pdf_loader.py:18-29` has `_CONVERTER: PdfConverter | None = None` + `_get_converter()` lazy init.
- **REQ-5** (formula-aware retrieval smoke): **PASS** — `run_socratic_tests.py:160-191` `test_formula_retrieval()` asserts `"$" in doc.page_content` for any top-3 chunk.
- **REQ-6** (marker model bake in Docker): **PASS** — `Dockerfile:36-40` `RUN MODEL_CACHE_DIR=/app/rag/index/marker-models TORCH_DEVICE_MODEL=cpu python -c "from marker.models import create_model_dict; create_model_dict()"`; `Dockerfile:52` `ENV MODEL_CACHE_DIR=./rag/index/marker-models`.
- **REQ-7** (NFR assertion script): **PASS** — `scripts/verify_latex.py` exists, asserts total ≥2000, prints per-source breakdown.
- **NFR-1** (≥2000 LaTeX occurrences): **PASS** — actual total = **2665** (display=708, inline=1957). Per Sears chapter: Cinemática 1=577, Cinemática 2=832, Dinámica 1=417, Dinámica 2pdf=748 (all ≥400). cuadernillo=43, formulas.md=48.
- **NFR-2** (smoke test pass): **PASS** — formula-retrieval PASS for all 3 formula queries (readable LaTeX surfaced, e.g. `$$v_{\text{med-x}} = \frac{...}{...}$$`); 26/26 socratic queries ran.
- **NFR-3** (no pymupdf4llm): **PASS** — 0 project hits (only `.venv/`). requirements.txt fully removed.

## Design compliance

- **Env var `MODEL_CACHE_DIR`** (not `SURYA_MODEL_CACHE_DIR`): **PASS** — `Dockerfile:37,52`, `scripts/preparar_indice_hf.py:20`, `docs/hf-space.md:28,108` all use `MODEL_CACHE_DIR` only. Confirmed intentional correction per Engram obs #177.
- **Bake path `rag/index/chroma/`**: **PASS** — committed (commit `2e692be`), 12 MB on disk, contains `chroma.sqlite3` + UUID dir, `col.count()` = 1374. < 100 MB Git-LFS cap.
- **`pymupdf4llm` removed from requirements.txt**: **PASS** (with W-1 design drift reconciled).
- **Scripts runnable**: **PASS** — `ast.parse` succeeds on all 4 modified scripts. `from rag.chain import generate_response` → `OK` (actual API is `generate_response`, not `build_chain`).

## Tasks completion

- **15/15 tasks done: PASS** — verify reconciled `tasks.md` to check 1.1, 1.2, 2.3, 4.4 (which were `[ ]` despite commits existing) and corrected the stale `SURYA_MODEL_CACHE_DIR` → `MODEL_CACHE_DIR` text in tasks 3.1 and 3.4.

## Acceptance criteria

- **1374 chunks**: PASS — `rag/index/chroma` count=1374, `data/chroma` count=1374 (both verified with `chromadb.PersistentClient`).
- **verify_latex PASS**: PASS — exits 0, prints `[PASS] LaTeX assertion passed (2665 ≥ 2000)`.
- **socratic smoke**: PASS — 26/26 queries completed; formula-retrieval PASS for all 3 formula queries; exit 0.
- **no pymupdf4llm**: PASS — 0 project hits.
- **marker model bake**: PASS — `Dockerfile:36-40` bakes via `create_model_dict()` with `MODEL_CACHE_DIR`.
- **bake committed**: PASS — commit `2e692be`, 12 MB, tracked.

## Next steps for orchestrator

- If PASS-WITH-WARNINGS: proceed to **sdd-archive** (verified post-reconciliation). 3 of 6 WARNINGs (W-1, W-2, W-6) are fully addressed in design.md "## Implementation Reconciliation". 2 (W-3, W-4) are future enhancements. 1 (W-5) resolves at archive.
- Save the design-drift findings (done — Engram obs #181).

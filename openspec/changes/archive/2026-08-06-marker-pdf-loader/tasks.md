# Tasks: marker-pdf-loader

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~136 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Loader swap + dependency + cuadernillo smoke | PR 1 | base: main; includes REQ-1, REQ-2, STABLE-1 |
| 2 | Re-index 5 PDFs + LaTeX verification + canonicity gate | PR 1 (cont.) | REQ-3, REQ-7; depends on Unit 1 |
| 3 | Deploy image marker bake + docs update | PR 1 (cont.) | REQ-4, REQ-5, PERF-1; depends on Unit 2 |
| 4 | Smoke test LaTeX assertion + commit + open PR | PR 1 (cont.) | REQ-6; final verification |

> All units fit in a single PR (~136 lines). No chaining needed.

## Phase 1: Foundation — Loader Swap + Dependency

- [x] 1.1 **Swap `rag/loaders/pdf_loader.py` to marker-pdf** — Replace `pymupdf4llm` import with `from marker.converters.pdf import PdfConverter`; add module-level `_CONVERTER = None` singleton; implement `_get_converter()` that calls `create_model_dict()` once and caches `PdfConverter(artifact_dict=...)`; set `disable_image_extraction=True`; `load_pdf()` calls `_CONVERTER(str(path))`, extracts markdown via `result.markdown`, returns `[Document(page_content=markdown, metadata={"source": str(path)})]`. Signature unchanged. Commit 1e3785f. (~35 lines) → REQ-1, REQ-7
- [x] 1.2 **Update `requirements.txt`** — Uncomment `marker-pdf>=1.10`; remove `pymupdf4llm>=0.0.10` line and its comment block (lines 13–17); add a note pointing to ADR 0001 supersession. Commit c145805. (~3 lines) → REQ-2
- [x] 1.3 **Cuadernillo smoke test (STABLE-1 gate)** — Run `python -c "from rag.loaders import load_pdf; load_pdf('data/pdfs/cuadernillo-fisica-1.pdf')"` with a 25-min timeout (retry: design estimated ~11.5 min on Mac MPS). If it hangs or errors, STOP — do not proceed to Phase 2. Capture process state for diagnosis. → STABLE-1

## Phase 2: Core — Re-Index + LaTeX Verification

- [x] 2.1 **Add canonicity gate to `scripts/indexar_pdfs.py`** — In `main()`, when `--pdfs-dir` equals default `data/pdfs/`, assert exactly 5 files matching `CANONICAL_PDFS = ["Cinemática 1.pdf", "Cinemática 2.pdf", "Dinámica 1.pdf", "Dinámica 2pdf.pdf", "cuadernillo-fisica-1.pdf"]`. Missing files → print list, `sys.exit(1)`. (~15 lines) → MODIFIED Single-Corpus Source
- [x] 2.2 **Create `scripts/verify_latex.py`** — Connect to `data/chroma/` via ChromaDB client; iterate all chunks whose `source` metadata matches a Sears chapter filename; count `$` and `$$` occurrences in `page_content`; assert total ≥ 2000 and each chapter ≥ 400; print PASS/FAIL with per-chapter breakdown; exit 1 on failure. (~45 lines) → REQ-3
- [x] 2.3 **Run full re-index** — Execute `python scripts/indexar_pdfs.py --reset` against the 5-PDF canonical set. Expect ~3–4h. Verify all 5 PDFs indexed with non-zero chunks. (User ran manually with `nohup` per batch strategy — 1374 chunks, 0 errors, ~5-7h actual.) → REQ-3, REQ-7
- [x] 2.4 **Run LaTeX verification** — Execute `python scripts/verify_latex.py`. Must PASS (≥2000 total `$`/`$$` across Sears chapters). If FAIL, investigate loader or corpus before proceeding. → REQ-3

## Phase 3: Integration — Deploy Image + Bake

- [x] 3.1 **Add marker model bake to `Dockerfile`** — After the existing embedding model RUN step, add: `RUN MODEL_CACHE_DIR=/app/rag/index/marker-models TORCH_DEVICE_MODEL=cpu python -c "from marker.models import create_model_dict; create_model_dict()"` and `chown -R user:user /app/rag/index/marker-models`. Add `ENV MODEL_CACHE_DIR=./rag/index/marker-models` to runtime config. Commit 42eef80. (~10 lines) → REQ-5
- [x] 3.2 **Re-bake `rag/index/chroma/`** — Execute `rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/`. Verify `du -sh rag/index/chroma/` < 100 MB. → REQ-4
- [x] 3.3 **Add comment to `scripts/preparar_indice_hf.py`** — Add a docstring note clarifying this script handles embedding models only; marker models are baked by the Dockerfile RUN step. (~5 lines) → REQ-5 (documentation)
- [x] 3.4 **Update `docs/hf-space.md`** — Update re-bake section: 5-PDF corpus (not cuadernillo-only), add `verify_latex.py` step, document `MODEL_CACHE_DIR` env var, note marker cache baked at build time, update cold-start budget if measured. Commit 5afd167. (~15 lines) → PERF-1, Reproducible Re-bake Workflow

## Phase 4: Verification — Smoke Test + Final Checks

- [x] 4.1 **Extend `scripts/run_socratic_tests.py` with LaTeX assertion** — After the query loop, add an `[ASSERT]` block: for 2–3 formula-targeting queries (e.g. "¿Cuál es la fórmula de la velocidad media?"), inspect retrieved chunks (via `rag.chain` internals or a thin wrapper) and assert at least one chunk contains `$` or `$$`. Report PASS/FAIL per query. (~8 lines) → REQ-6
- [x] 4.2 **Run smoke test suite** — Execute `python scripts/run_socratic_tests.py`. Verify LaTeX assertion PASSes for formula queries. Review report for regressions. → REQ-6
- [x] 4.3 **Verify backward compatibility** — Confirm `scripts/indexar_pdfs.py` ran without type errors (Phase 2.3). Confirm `rag/chain.py` retrieval path unchanged (no code edits needed there). → REQ-7
- [x] 4.4 **Stage and commit** — `git add` all changed files: `rag/loaders/pdf_loader.py`, `requirements.txt`, `scripts/indexar_pdfs.py`, `scripts/verify_latex.py`, `scripts/run_socratic_tests.py`, `scripts/preparar_indice_hf.py`, `Dockerfile`, `docs/hf-space.md`, `rag/index/chroma/`. Commits landed as 9 work-unit commits (1e3785f, c145805, d876021, 8b3d6c3, 42eef80, eb5131d, 5afd167, ad96f9c, 2e692be) rather than a single commit per Work-Unit Commits skill. → All REQs

## Traceability Matrix

| REQ / NFR | Task IDs |
|-----------|----------|
| REQ-1 (PDF Loader Uses marker-pdf) | 1.1 |
| REQ-2 (marker-pdf Runtime Dependency) | 1.2 |
| REQ-3 (Re-Index LaTeX-Rich Chunks) | 2.2, 2.3, 2.4 |
| REQ-4 (Re-Baked Deploy Artifact) | 3.2 |
| REQ-5 (Marker Models Baked Into Image) | 3.1, 3.3 |
| REQ-6 (Smoke Test Asserts LaTeX) | 4.1, 4.2 |
| REQ-7 (Loader Contract Backward Compat) | 1.1, 2.1, 4.3 |
| PERF-1 (Cold-Start Budget) | 3.4 |
| STABLE-1 (Cuadernillo Smoke) | 1.3 |
| CONFIG-1 (Device Detection Unchanged) | 1.1 (implicit — no EMBEDDINGS_DEVICE coupling) |
| MODIFIED Single-Corpus Source | 2.1 |
| MODIFIED Reproducible Re-bake Workflow | 2.1, 3.4 |

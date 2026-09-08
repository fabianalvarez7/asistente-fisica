# corpus-rebake Specification

> **Updated capability spec** — last updated on `2026-09-08` after reverting `marker-pdf` → `pymupdf4llm` (perf inviable on consumer hardware; see `docs/adr/0001-pdf-loader-marker.md`).
> Source: `openspec/changes/archive/2026-08-06-marker-pdf-loader/specs/corpus-rebake/spec.md`
> First archived: `deploy-hf-spaces` change on `2026-06-28`.
> Future changes to this capability SHOULD create a delta spec against this file.

## Purpose

Produce a fresh ChromaDB index baked from the project's PDF corpus (current state: 10 PDFs in `data/pdfs/` plus optional `formulas.md`) and committed to `rag/index/chroma/`. The index is built with the `pymupdf4llm` PDF loader, which is fast (~10-20 seconds per 60-page PDF on Mac MPS) but does NOT recover formulas rendered as images in the source PDF. The re-bake is required on corpus change or loader swap, runs locally with `python scripts/indexar_pdfs.py --reset`, and completes in under 5 minutes on Mac MPS for the current corpus. The result MUST be a non-empty `data/chroma/` (≥ 1 chunk) before being committed. Deploy-target-agnostic and MUST NOT change backend code (`rag/chain.py`, retrievers, `app/main.py`); it only re-runs the existing indexing script and commits the result.

> **Removed NFR (was: ≥2000 LaTeX occurrences via `scripts/verify_latex.py`)**: the previous marker-pdf-derived NFR no longer applies; `pymupdf4llm` cannot recover formulas-as-images. The script now reports LaTeX counts per source as informational only. `data/markdown/formulas.md` supplements the gap.

## Requirements

### Requirement: Single-Corpus Source

The re-bake SHALL consume exactly 5 canonical PDFs in `data/pdfs/`: `Cinemática 1.pdf`, `Cinemática 2.pdf`, `Dinámica 1.pdf`, `Dinámica 2pdf.pdf`, and `cuadernillo-fisica-1.pdf`. An optional `formulas.md` markdown file may also be present. The canonicity gate in `scripts/indexar_pdfs.py` (the `CANONICAL_PDFS` constant + `_check_canonical_corpus()` function) SHALL enforce this list before indexing; if any PDF is missing, the script MUST raise `FileNotFoundError` (or `sys.exit(1)`) with a clear list of missing files.

#### Scenario: All 5 canonical PDFs present

- GIVEN `data/pdfs/` contains all 5 canonical PDFs (and optionally `formulas.md`)
- WHEN the bake script runs
- THEN every chunk in the resulting index is traceable to one of those sources
- AND no chunks from non-canonical PDFs survive

#### Scenario: Missing canonical PDF aborts cleanly

- GIVEN `data/pdfs/` is missing one of the 5 canonical PDFs
- WHEN the bake script runs
- THEN the script aborts before indexing with a clear error listing the missing files
- AND no partial index is produced

### Requirement: Stale Index Replacement

The re-bake SHALL overwrite the stale `rag/index/chroma/` (variable chunk count) with a fresh index built from the 5-PDF corpus. The fresh chunk count SHALL be **1374** (1360 chunks from 5 PDFs + 14 chunks from `formulas.md`), confirming the new corpus fully indexed.

#### Scenario: Fresh index supersedes the stale one

- GIVEN `rag/index/chroma/` holds a stale index (any chunk count)
- WHEN the re-bake completes and the new index is copied into place
- THEN `vector_store.count()` against the new path returns 1374
- AND the stale chunks no longer exist in the collection

### Requirement: Cosine Space Preservation

The fresh index SHALL be created in the same cosine space (`hnsw:space: cosine`) the runtime expects. If the local `data/chroma/` collection is still in L2 space (legacy from before the cosine metadata was added), the re-bake SHALL use `--reset` to recreate the collection in cosine space rather than reusing the legacy L2 collection.

#### Scenario: L2 → cosine migration via reset

- GIVEN the local `data/chroma/` collection is in L2 space
- WHEN the re-bake runs with `--reset`
- THEN the new collection is created with cosine space metadata
- AND `similarity_search_with_scores` returns cosine distances, not L2 distances

#### Scenario: Idempotent on an already-cosine collection

- GIVEN the local `data/chroma/` is already cosine
- WHEN the re-bake runs
- THEN the cosine space is preserved and chunks are added without space drift

### Requirement: Committed Baked Artifact

The fresh index SHALL be committed to `rag/index/chroma/` (tracked in git) so local dev and the HF Space both load it from the repo. The baked path SHALL match the value of `CHROMA_PERSIST_DIR` used at runtime. The committed bake is approximately 12 MB on disk (well under the 100 MB Git-LFS per-file cap).

#### Scenario: Bake is committed and consumed

- GIVEN the re-bake produced `rag/index/chroma/`
- WHEN the changes are committed and the app boots (local or on the Space)
- THEN `vector_store.count()` loads from `rag/index/chroma/` and returns 1374
- AND no indexing step runs at boot

### Requirement: Reproducible Re-bake Workflow

The re-bake SHALL be reproducible from a clean clone by a documented two-step command sequence: (1) `python scripts/indexar_pdfs.py --reset` to re-bake `data/chroma/`, then (2) `python scripts/verify_latex.py` to confirm the bake is non-empty (informational — see NFR note below). The workflow SHALL be documented in `docs/hf-space.md`. The bake completes in under 5 minutes on Mac MPS for the current 10-PDF corpus. The workflow SHALL NOT require network access beyond the corpus files in `data/pdfs/` and the embedding model snapshot already baked into the Docker image (`rag/index/hf-model/`). No PDF-loader model download is required because the loader is `pymupdf4llm`.

#### Scenario: Clean-clone re-bake

- GIVEN a fresh clone of the repo (with the PDFs in `data/pdfs/`)
- WHEN the documented re-bake command sequence runs
- THEN a fresh `data/chroma/` is produced (~4668 chunks for the current 10-PDF + `formulas.md` corpus as of 2026-09-08)
- AND `verify_latex.py` exits 0 (informational pass — see NFR note)
- AND the developer did not manually edit env vars or path constants

#### Scenario: Corpus change re-bake

- GIVEN one of the corpus PDFs is updated (e.g., a new edition is dropped in)
- WHEN the developer re-runs the documented re-bake and copies `data/chroma/` to `rag/index/chroma/`
- THEN the next deploy serves the updated corpus
- AND `docs/hf-space.md` documents that the baked index must be re-committed on corpus change

### Requirement: PDF Loader Uses pymupdf4llm

The PDF loader at `rag/loaders/pdf_loader.py` SHALL use `pymupdf4llm` to extract markdown from PDFs. The `marker-pdf` library SHALL NOT be imported or used anywhere in the project (including transitive deps via `requirements.txt`). The loader SHALL expose a `load_pdf(path) -> list[Document]` signature unchanged from the previous implementation (caller compatibility in `indexar_pdfs.py` and `chain.py`).

#### Scenario: Loader uses pymupdf4llm

- GIVEN the loader is at `rag/loaders/pdf_loader.py`
- WHEN the loader is called with a PDF path
- THEN it returns a list of `Document` objects whose `page_content` is markdown extracted by `pymupdf4llm` (text + inline LaTeX; NOT formulas-as-images)
- AND `grep -rn "marker-pdf\|surya" --include="*.py" --include="*.txt" rag/ scripts/ app/ dashboard/ docs/` returns 0 hits (excluding the historical ADR `0001-pdf-loader-marker.md`)

### Requirement: No PDF Loader Model Required

The `pymupdf4llm` loader SHALL NOT require any model download, snapshot bake, or large dependency in the Docker image. The `Dockerfile` SHALL NOT include any step that downloads or caches `marker-pdf` / `surya-ocr` / or any other PDF-OCR model. The runtime `ENV` block SHALL NOT reference `MODEL_CACHE_DIR` (a marker-pdf relic).

#### Scenario: Cold-start does not load PDF models

- GIVEN the Docker image has been built with the current loader stack
- WHEN the Space boots and the first `/chat` request arrives
- THEN no PDF-loader model load occurs (pymupdf4llm is a thin wrapper over PyMuPDF)
- AND no HTTP request is made to download PDF models

### Requirement: Formula-Aware Retrieval Smoke Test

The `scripts/run_socratic_tests.py` smoke test suite SHALL include a `test_formula_retrieval()` function that asserts a formula-aware query (e.g., "fórmula de velocidad media") returns relevant chunks in the top-3 retrieved results. The chunks MAY come from `data/markdown/formulas.md` (the supplement) when the source PDF has formulas-as-images that `pymupdf4llm` cannot recover. The test SHALL print PASS/FAIL with chunk previews. The assertion MAY be non-fatal (continue after FAIL) for manual review workflows.

#### Scenario: Formula query returns relevant chunks

- GIVEN a freshly baked `data/chroma/` index
- WHEN `python scripts/run_socratic_tests.py` runs and `test_formula_retrieval()` is called
- THEN at least 1 of the top-3 retrieved chunks is relevant to the formula query
- AND the test prints PASS with the chunk previews

### Requirement: Bake Completeness Report Script

A `scripts/verify_latex.py` script SHALL exist and SHALL report per-source LaTeX (`$` and `$$`) counts across all chunks in the freshly baked ChromaDB. The script SHALL exit with code 0 if the store is non-empty (≥ 1 chunk) and 1 if the store is empty. The previous ≥2000 LaTeX NFR was tied to the `marker-pdf` loader and is no longer applicable with `pymupdf4llm`; the script now reports counts as informational only (PDFs with formulas-as-images will show 0 by design — see ADR `0001-pdf-loader-marker.md`).

#### Scenario: Fresh index passes the NFR

- GIVEN a freshly baked index from the 5-PDF corpus
- WHEN `python scripts/verify_latex.py` runs
- THEN the script counts `$` and `$$` occurrences across all chunks
- AND the total is ≥2000
- AND the script prints PASS and exits 0

#### Scenario: Stale or partial index fails the NFR

- GIVEN a partial or stale index with <2000 LaTeX occurrences
- WHEN `python scripts/verify_latex.py` runs
- THEN the script prints FAIL with a per-source breakdown
- AND exits 1

## Non-Functional Requirements

### NFR-1: LaTeX Coverage

The baked index SHALL have ≥2000 LaTeX occurrences (sum of display `$$...$$` and inline `$...$` formulas) across the 5 canonical PDFs. This threshold ensures the Socratic layer can surface formula-rich chunks to the LLM. Observed on 2026-08-06: 2665 (display=708, inline=1957). Per Sears chapter: Cinemática 1=577, Cinemática 2=832, Dinámica 1=417, Dinámica 2pdf=748 (all ≥400 individually).

### NFR-2: Smoke Test Pass

The `scripts/run_socratic_tests.py` smoke suite (including `test_formula_retrieval()`) SHALL pass on a fresh re-bake. Observed: 26/26 queries ran, formula retrieval PASS for all 3 formula queries.

### NFR-3: No pymupdf4llm in Project

`pymupdf4llm` SHALL NOT appear in `requirements.txt` or any project `.py` file. The dev `.venv/` may retain the installed package as a harmless leftover, but no code path imports or uses it. `grep -r "pymupdf4llm" --include="*.py" --include="*.txt" .` SHALL return 0 hits outside the `.venv/` directory.

## Notes from Archive

This spec was updated by the `marker-pdf-loader` change (2026-08-06). The 5-PDF canonical corpus and marker-pdf loader replaced the 1-PDF cuadernillo-only + pymupdf4llm setup from the previous `deploy-hf-spaces` change. Re-bake yields 1374 chunks (1360 from 5 PDFs + 14 from `formulas.md`); NFR ≥2000 LaTeX (observed 2665). Verdict: PASS-WITH-WARNINGS (6 non-blocking WARNINGs reconciled in `design.md` and `verify-report.md`).

**Previous archived version** (2026-06-28, from `deploy-hf-spaces` change): single PDF (`cuadernillo-fisica-1.pdf`), pymupdf4llm loader, 25 chunks. That setup was insufficient for the Socratic layer because pymupdf4llm lost all LaTeX formulas; the marker-pdf swap is the fix.

## References

- `openspec/changes/archive/2026-08-06-marker-pdf-loader/` (this change's full archive)
- `openspec/changes/archive/2026-08-06-marker-pdf-loader/specs/corpus-rebake/spec.md` (change-specific source)
- `openspec/changes/archive/2026-06-28-deploy-hf-spaces/` (prior canonical state)
- `openspec/changes/archive/2026-06-28-deploy-hf-spaces/specs/corpus-rebake/spec.md` (prior delta spec)
- `openspec/specs/hf-spaces-deploy/spec.md` (companion capability)
- Engram observation: `sdd/marker-pdf-loader/apply-progress` (obs #178)
- Engram observation: `sdd/marker-pdf-loader/verify-findings` (obs #181)
- Engram observation: `marker-pdf-loader/design-reconciliation` (obs #182)

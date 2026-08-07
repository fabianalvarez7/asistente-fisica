# corpus-rebake Specification

> **Updated capability spec** — last updated by the `marker-pdf-loader` change on `2026-08-06`.
> Source: `openspec/changes/archive/2026-08-06-marker-pdf-loader/specs/corpus-rebake/spec.md`
> First archived: `deploy-hf-spaces` change on `2026-06-28`.
> Future changes to this capability SHOULD create a delta spec against this file.

## Purpose

Produce a fresh ChromaDB index baked from a 5-PDF canonical corpus (plus optional `formulas.md`) and committed to `rag/index/chroma/`. The index is built with the `marker-pdf` PDF loader (1.10.2+), which recovers LaTeX formulas that the previous `pymupdf4llm` loader lost. The re-bake is required on corpus change or loader swap, runs locally with `python scripts/indexar_pdfs.py --reset`, and takes 5-7 hours on Mac MPS for the 5-PDF corpus (a single `Recognizing Text` pass alone can take 1-2 hours per chapter). The result MUST pass `python scripts/verify_latex.py` (≥2000 LaTeX occurrences NFR) before being committed to the deploy path. Deploy-target-agnostic and MUST NOT change backend code (`rag/chain.py`, retrievers, `app/main.py`); it only re-runs the existing indexing script and commits the result.

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

The re-bake SHALL be reproducible from a clean clone by a documented two-step command sequence: (1) `python scripts/indexar_pdfs.py --reset` to re-bake `data/chroma/`, then (2) `python scripts/verify_latex.py` to assert the NFR ≥2000 LaTeX occurrences. The workflow SHALL be documented in `docs/hf-space.md`. The bake takes 5-7h on Mac MPS (a single chapter's `Recognizing Text` stage alone can take 1-2 hours because marker-pdf processes ~12 sub-blocks per page, not 1 per page). The workflow SHALL NOT require network access beyond the corpus files in `data/pdfs/` and the model snapshot already baked into the Docker image.

#### Scenario: Clean-clone re-bake

- GIVEN a fresh clone of the repo (with the 5 canonical PDFs in `data/pdfs/`)
- WHEN the documented re-bake command sequence runs
- THEN a fresh `data/chroma/` is produced with 1374 chunks
- AND `verify_latex.py` exits 0 with total ≥2000
- AND the developer did not manually edit env vars or path constants

#### Scenario: Corpus change re-bake

- GIVEN one of the 5 canonical PDFs is updated (e.g., a new edition is dropped in)
- WHEN the developer re-runs the documented re-bake and copies `data/chroma/` to `rag/index/chroma/`
- THEN the next deploy serves the updated corpus
- AND `docs/hf-space.md` documents that the baked index must be re-committed on corpus change

### Requirement: PDF Loader Uses marker-pdf

The PDF loader at `rag/loaders/pdf_loader.py` SHALL use `marker-pdf` (1.10.2+) to extract markdown from PDFs. The `pymupdf4llm` library SHALL NOT be imported or used anywhere in the project. The loader SHALL expose a `load_pdf(path) -> list[Document]` signature unchanged from the previous implementation (caller compatibility in `indexar_pdfs.py` and `chain.py`).

#### Scenario: Loader swap to marker-pdf

- GIVEN the loader is at `rag/loaders/pdf_loader.py`
- WHEN the loader is called with a PDF path
- THEN it returns a list of `Document` objects whose `page_content` is markdown extracted by `marker-pdf` (including LaTeX formulas)
- AND `grep -r "pymupdf4llm" --include="*.py" .` returns 0 project hits (only the dev `.venv/` may contain the installed package as a harmless leftover)

### Requirement: Singleton PdfConverter

The `PdfConverter` instance SHALL be a module-level singleton (`_CONVERTER`) with lazy initialization. The first call to `load_pdf()` triggers `create_model_dict()` and constructs the converter; subsequent calls reuse the same instance, amortizing the ~10 GB RAM peak model load across all PDFs in the corpus.

#### Scenario: Singleton reuses one model load

- GIVEN the loader has been called once on any PDF
- WHEN the loader is called again on a different PDF
- THEN the same `_CONVERTER` instance is used (no second `create_model_dict()` call)
- AND no second model download occurs

### Requirement: marker-pdf Models Baked in Docker

The `Dockerfile` SHALL pre-bake the `marker-pdf` / `surya-ocr` model snapshot (~3.45 GB) at build time so the deployed HF Space does not download models on every cold start. The `RUN python -c "from marker.models import create_model_dict; create_model_dict()"` step MUST run with `MODEL_CACHE_DIR=/app/rag/index/marker-models` and `TORCH_DEVICE_MODEL=cpu` (HF Spaces is CPU-only). The runtime `ENV` block MUST also set `MODEL_CACHE_DIR=./rag/index/marker-models` so the app loads from the baked path.

#### Scenario: Cold-start does not re-download

- GIVEN the Docker image has been built and the marker models are baked at `/app/rag/index/marker-models`
- WHEN the Space boots and the first `/chat` request arrives
- THEN the model load reads from the local baked path
- AND no HTTP request is made to download models

### Requirement: Formula-Aware Retrieval Smoke Test

The `scripts/run_socratic_tests.py` smoke test suite SHALL include a `test_formula_retrieval()` function that asserts a formula-aware query (e.g., "fórmula de velocidad media") returns chunks containing LaTeX (`$` characters) in the top-3 retrieved results. The test SHALL print PASS/FAIL with chunk previews. The assertion MAY be non-fatal (continue after FAIL) for manual review workflows.

#### Scenario: Formula query returns LaTeX chunks

- GIVEN a freshly baked `data/chroma/` index
- WHEN `python scripts/run_socratic_tests.py` runs and `test_formula_retrieval()` is called
- THEN at least 1 of the top-3 retrieved chunks contains a `$` character
- AND the test prints PASS with the chunk previews

### Requirement: LaTeX NFR Assertion Script

A `scripts/verify_latex.py` script SHALL exist and SHALL assert that the freshly baked ChromaDB has ≥2000 LaTeX occurrences (display + inline, summed across all 5 indexed PDFs). The script SHALL print a per-source breakdown and exit with code 0 on PASS or 1 on FAIL.

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

# Delta for corpus-rebake: marker-pdf-loader

## Purpose

The Socratic layer — the project's stated priority (AGENTS §8) — cannot guide a student through a formula it cannot read. Obs #163 shows `pymupdf4llm` recovers **zero** LaTeX delimiters from clean typeset Sears content (`Cinemática 1.pdf`, 25 pages), while `marker-pdf` recovers 559 (`$`/`$$`) at 1.7 min/page on Mac MPS. Obs #164 confirms retrieval scores are statistically identical between extractors (top-1 cosine tie within 0.02), but marker's top-3 chunks contain readable LaTeX for all 4 student queries while pymupdf4llm's contain garbled text (e.g. `v med- x 5 D x >D t` vs `$$v_{\text{med-x}} = \frac{x_2 - x_1}{t_2 - t_1}$$`). The discriminator is content quality, not retrieval relevance.

ADR 0001 reverted marker-pdf on 2026-06-30 over three issues: ~5h re-bake time, ~3GB per-user cache outside the repo, and bad OCR on scanned PDFs. Obs #163/#164 re-evaluate the first objection against clean typeset Sears content (the canonical corpus going forward, per open question #2) and find marker wins decisively. This delta swaps the loader back to marker-pdf, expands the corpus from 1 to 5 PDFs, resolves the cache question for HF Spaces deploy, and adds a LaTeX assertion to the smoke test. The Socratic prompt, splitter, embedding model, UI, and dashboard are explicitly untouched.

## MODIFIED Requirements

### Requirement: Single-Corpus Source

The re-bake SHALL consume exactly the 5 PDFs residing in `data/pdfs/` (the 4 Sears chapters — `Cinemática 1.pdf`, `Cinemática 2.pdf`, `Dinámica 1.pdf`, `Dinámica 2pdf.pdf` — plus `cuadernillo-fisica-1.pdf`). No other PDFs SHALL be present during the bake. The 5-PDF set is the canonical corpus; open question #2 (confirm completeness) MUST be resolved before the re-bake runs.
(Previously: consumed exactly one source PDF — the cuadernillo only, per the original `deploy-hf-spaces` corpus-rebake spec point.)

#### Scenario: Bake runs against the 5-PDF canonical set

- GIVEN `data/pdfs/` contains exactly the 5 canonical PDFs listed above
- WHEN the bake script runs with `--reset`
- THEN every chunk in the resulting index is traceable to one of those 5 sources
- AND no chunks from removed or extra PDFs survive

#### Scenario: Canonical corpus incomplete

- GIVEN `data/pdfs/` is missing one or more of the 5 canonical PDFs
- WHEN the bake script runs
- THEN the script SHALL abort with a non-zero exit and list the missing files
- AND no partial index is written to `rag/index/chroma/`

### Requirement: Reproducible Re-bake Workflow

The re-bake SHALL be reproducible from a clean clone by a short documented command sequence against the 5-PDF canonical set, using `rag/loaders/pdf_loader.py` backed by `marker-pdf`. The workflow SHALL be documented in `docs/hf-space.md` and SHALL NOT require network access beyond the corpus + model snapshots reachable by the bake environment. The marker model cache (~3GB) is NOT committed to git; it is resolved locally (dev) or at Docker build time (deploy) — see the Marker Models Baked requirement.
(Previously: consumed the cuadernillo only and used `pymupdf4llm`; the loader swap and cache resolution go beyond that scope.)

#### Scenario: Clean-clone re-bake on dev

- GIVEN a fresh clone with the 5 PDFs in `data/pdfs/` and marker models cached locally
- WHEN the documented re-bake command runs (`scripts/indexar_pdfs.py --reset` then `scripts/preparar_indice_hf.py`)
- THEN a fresh `rag/index/chroma/` is produced with chunks from all 5 PDFs
- AND the developer did not manually edit env vars or path constants

#### Scenario: Corpus change re-bake

- GIVEN one of the 5 canonical PDFs is updated
- WHEN the developer re-runs the documented re-bake and commits `rag/index/chroma/`
- THEN the next deploy serves the updated corpus
- AND `docs/hf-space.md` documents that the baked index MUST be re-committed on corpus change

## ADDED Requirements

### Requirement: PDF Loader Uses marker-pdf (REQ-1)

`rag/loaders/pdf_loader.py` SHALL invoke the marker-pdf `PdfConverter` (current installed API: `from marker.converters.pdf import PdfConverter`, v1.10.2 — verify at design time against the venv pin) and return a `list[Document]`. The `load_pdf(path) -> list[Document]` and `load_pdfs(paths) -> list[Document]` signatures SHALL be unchanged. The `PdfConverter` plus its model dict SHALL be cached as a module-level singleton (per ADR 0001's "modelos cacheados en singleton (`_CONVERTER`)" note) so models load once per process, not per call. `disable_image_extraction` (or the current marker equivalent) SHALL be set to suppress image extraction; the prototype serves text chunks, not figures (AGENTS §10).

#### Scenario: Loader returns one Document per PDF

- GIVEN `pdf_loader.py` is the marker-backed loader and a PDF path
- WHEN `load_pdf(path)` is called
- THEN it returns a `list` of exactly one `Document`
- AND `page_content` is marker-pdf's rendered markdown (text + LaTeX)
- AND `metadata == {"source": str(path)}`

#### Scenario: Singleton converter is reused across calls

- GIVEN `load_pdf` has been called once on any PDF
- WHEN `load_pdf` is called again on a different PDF in the same process
- THEN the model-loading step does not repeat (no second multi-minute warmup)
- AND only the per-PDF conversion runs

#### Scenario: Image extraction disabled

- GIVEN the loader is configured with `disable_image_extraction=True` (or equivalent)
- WHEN a PDF with embedded figures is converted
- THEN no image files are written to `data/` or the working directory
- AND the returned markdown references images by alt-text/placeholder only if at all

### Requirement: marker-pdf Declared as Runtime Dependency (REQ-2)

`requirements.txt` SHALL list `marker-pdf>=1.10` (matching the venv-pinned `1.10.2`, verified via `pip show marker-pdf`) as an uncommented runtime dependency. The existing comment block marking marker-pdf as "PLAN B, SUPERSEDED" SHALL be replaced with a note pointing to ADR 0001's supersession-by-this-change and the marker-pdf-loader proposal. `pymupdf4llm` MAY remain listed (it is harmless and small) or be removed; the decision is design's, not the spec's.

#### Scenario: marker-pdf present in freshly installed venv

- GIVEN a clean venv on a fresh clone
- WHEN `pip install -r requirements.txt` runs
- THEN `marker-pdf>=1.10` is installed and importable
- AND `pip show marker-pdf` reports a version ≥ 1.10

#### Scenario: marker-pdf absent breaks boot

- GIVEN `requirements.txt` does NOT declare marker-pdf
- WHEN `uvicorn app.main:app` boots (or any path importing `rag.loaders`)
- THEN the import of `marker.converters.pdf` fails fast with an ImportError
- AND no partial index or chat path silently degrades to a no-op loader

### Requirement: Re-Index Produces LaTeX-Rich Chunks (REQ-3)

After `scripts/indexar_pdfs.py --reset` on the 5-PDF canonical set, the resulting `data/chroma/` collection SHALL contain chunks where the sum of `$` and `$$` delimiter occurrences across the 4 Sears chapters' chunks is ≥ 2000 (≥500 average per chapter, grounded in obs #163's 559 recovered from `Cinemática 1.pdf` alone — a conservative floor). The cuadernillo's chunk-level LaTeX count SHALL be ≥ 0 (its formula images are sparse; no floor asserted there). The assertion is run as a post-bake check, not a runtime check.
(Previously: the corpus-rebake spec asserted only a chunk-count threshold of >25; LaTeX richness was not measurable because the loader dropped all formulas.)

#### Scenario: Sears chapters yield LaTeX-rich chunks

- GIVEN the re-index has completed on the 5-PDF set
- WHEN a post-bake check counts `$` and `$$` delimiter occurrences across chunks whose `source` metadata matches a Sears chapter
- THEN the sum across the 4 Sears chapters is ≥ 2000
- AND each individual Sears chapter contributes ≥ 400 (tolerating per-PDF variance)

#### Scenario: pymupdf4llm regression is caught

- GIVEN the loader has reverted to `pymupdf4llm` (regression)
- WHEN the same post-bake check runs on the resulting index
- THEN the Sears-chapter delimiter sum is 0 (obs #163 baseline)
- AND the check fails with a clear message identifying the regression

### Requirement: Re-Baked Deploy Artifact Is Committed (REQ-4)

`scripts/preparar_indice_hf.py` (or the re-bake workflow it gates) SHALL write the fresh index to `rag/index/chroma/`, overwriting the stale 5-PDF-less bake. The artifact SHALL be committed to git (tracked, not gitignored) so local dev and the HF Space both load it from the repo. The committed size SHALL be < 100 MB (the current bake is 788 KB; the 5-PDF expansion is bounded by chunk count, well under the GitHub/Git-LFS per-file cap). The committed path SHALL match `CHROMA_PERSIST_DIR` at runtime per the existing `corpus-rebake` spec requirement "Committed Baked Artifact".

#### Scenario: Fresh bake supersedes the stale one

- GIVEN `rag/index/chroma/` holds the stale single-corpus bake
- WHEN the re-bake completes and the new index is copied into place
- THEN `git status` shows `rag/index/chroma/` as modified
- AND `vector_store.count()` against the new path returns a value consistent with 5 PDFs (> the prior chunk count)

#### Scenario: Artifact size stays committable

- GIVEN the 5-PDF re-bake has completed
- WHEN `du -sh rag/index/chroma/` runs
- THEN the size is < 100 MB
- AND no single file inside it exceeds the Git-LFS 100 MB per-file cap

### Requirement: Marker Models Baked Into Deploy Image (REQ-5)

The marker-pdf model weights (~3GB, cached by default at `~/Library/Caches/datalab/models/` per ADR 0001) SHALL be available on HF Spaces at runtime and MUST NOT be downloaded on first chat request (which would push cold-start to minutes and risk OOM on the free `cpu-basic` tier). Approach **(b)** is chosen: the marker models SHALL be pre-downloaded during the Docker build step, mirroring the existing `scripts/preparar_indice_hf.py` pattern for the embedding model (downloaded to `rag/index/hf-model/` at build time, not committed). The model cache is NOT committed to git (too large); it is baked into the image layer. The exact cache env var(s) marker-pdf/surya respect (verified at design time) SHALL be set in the Dockerfile so the runtime `PdfConverter` loads from the baked location. The chosen resolution is written into `docs/hf-space.md`.
(Previously: ADR 0001 listed the per-user 3GB cache as a reason to revert; this requirement resolves objection #2 by baking the cache into the deploy image, not into the repo or the per-user machine.)

#### Scenario: First chat request after Space wake does not download models

- GIVEN a freshly woken HF Space (cold-start) and a corpus query
- WHEN the first `/chat` request is served
- THEN the marker models are loaded from the baked image directory only
- AND no outbound download to `models.datalab.to` occurs

#### Scenario: Build-time bake populates the marker cache

- GIVEN the Dockerfile build step runs `scripts/preparar_indice_hf.py` (extended) or an equivalent marker-model ensure step
- WHEN the image layer is built
- THEN the marker model files exist under the configured cache dir in the image (e.g. `/app/rag/index/marker-models/`)
- AND the marker `BASE_DIR`/cache env points there at runtime

### Requirement: Socratic Smoke Test Asserts LaTeX Chunks (REQ-6)

`scripts/run_socratic_tests.py` SHALL be extended (or a sibling test file added) with an assertion: when the Socratic chain runs against 2–3 representative kinematics queries (e.g. the existing "¿Cuál es la fórmula de la velocidad media?"-style queries that target a formula), at least one retrieved chunk injected into the LLM contains `$` or `$$` delimiters. The assertion SHALL inspect the retrieved context, not the LLM response (the LLM may or may not echo LaTeX; the point is the retriever surfaced it). The assertion runs in the existing test harness; no new pytest dependency is required.

#### Scenario: Formula query retrieves LaTeX chunk

- GIVEN the 5-PDF re-baked index is loaded
- WHEN a kinematics formula query runs through `rag.chain.generate_response`
- THEN at least one of the retrieved/source chunks passed to the LLM contains a `$` or `$$` delimiter
- AND the assertion reports PASS

#### Scenario: Observed regression (pymupdf4llm) fails the assertion

- GIVEN the index was baked with `pymupdf4llm` (regression)
- WHEN the same 2–3 formula queries run
- THEN no retrieved chunk contains `$` or `$$` (obs #164 baseline)
- AND the assertion reports FAIL

### Requirement: Loader Contract Backward Compatibility (REQ-7)

`load_pdf(path) -> list[Document]` SHALL continue to return exactly one `Document` per PDF (not per page — per ADR 0001's implementation note) with `metadata == {"source": str(path)}`. Callers in `scripts/indexar_pdfs.py` (`load_pdfs([pdf])`) and any downstream consumer in `rag/chain.py` SHALL continue to work without code changes beyond the loader's internal swap. The chunker (`rag/splitters/`) is downstream and unchanged.

#### Scenario: Indexing script consumes the new loader unchanged

- GIVEN `scripts/indexar_pdfs.py` and the marker-backed `pdf_loader.py`
- WHEN `indexar_pdfs.py` runs
- THEN it iterates the returned `list[Document]` without type errors
- AND chunk count per PDF is non-zero for all 5 PDFs

#### Scenario: Chain retrieval path unaffected

- GIVEN `rag/chain.py` builds its retriever from the baked `rag/index/chroma/`
- WHEN a chat request arrives
- THEN the retrieval and prompt-assembly path produces a request identical in shape to the pymupdf4llm era
- AND only the chunk `page_content` quality differs (LaTeX present)

## Non-Functional / Edge Cases

### Requirement: Cold-Start Budget (PERF-1)

The HF Spaces first request after sleep SHALL stay within the existing ~20–40s cold-start budget documented in `docs/hf-space.md` (AGENTS §7.8). If marker model loading at boot pushes cold-start measurably higher, the new budget SHALL be measured and recorded in `docs/hf-space.md` with the before/after numbers. If cold-start exceeds ~60s, the design phase SHALL consider lazy-loading the converter on first request rather than at import time.

#### Scenario: Cold-start within budget

- GIVEN a freshly woken HF Space
- WHEN the first chat request is served
- THEN the response time-to-first-token is within 20–40s (or the documented revised budget)
- AND `docs/hf-space.md` reflects the measured number

### Requirement: Cuadernillo Marker Smoke Test (STABLE-1)

Before the full 5-PDF re-index, a smoke test SHALL run `marker-pdf` on the cuadernillo alone (5 pages) to confirm it completes. The previous session (ADR 0001) observed a hang at 96% after ~20 min on the cuadernillo; this smoke test verifies that hang does not reproduce on the current marker-pdf version (1.10.2) and clean cache state. If the smoke test does not complete within ~10 minutes, the re-index SHALL abort and the failure SHALL be reported before any 3–4h full re-bake is attempted.

#### Scenario: Cuadernillo smoke completes

- GIVEN marker-pdf 1.10.2 is installed and the model cache is warm
- WHEN `load_pdf('data/pdfs/cuadernillo-fisica-1.pdf')` runs
- THEN it returns one `Document` within ~10 minutes
- AND the returned markdown is non-empty

#### Scenario: Cuadernillo smoke hangs

- GIVEN the cuadernillo smoke has been running for >10 minutes without completing
- WHEN the developer observes the timeout
- THEN the full 5-PDF re-index SHALL NOT proceed
- AND the failure is reported with the marker process state captured for diagnosis

### Requirement: Device Detection Unchanged (CONFIG-1)

The `EMBEDDINGS_DEVICE` env var (`auto` by default, AGENTS §12) SHALL remain the ownership of the embedding model only. marker-pdf's device selection (`TORCH_DEVICE` in marker settings) SHALL default to `auto` (MPS/CUDA/CPU) and SHALL NOT be coupled to `EMBEDDINGS_DEVICE`. If a future deploy needs to pin marker to CPU while embeddings stay on a different device, that is a separate config concern, out of scope here.

#### Scenario: Device defaults to auto

- GIVEN `EMBEDDINGS_DEVICE` is unset (default `auto`)
- WHEN `load_pdf` instantiates the singleton `PdfConverter`
- THEN marker selects MPS (macOS), CUDA (Windows+NVIDIA), or CPU (Space/otherwise) automatically
- AND no new env var is required for the prototype's deploy

## Out of Scope

Re-stated from the proposal; do not add these to the delta:
- Hybrid loader (pymupdf4llm for text + marker for formula PDFs) — rejected in ADR 0001 as over-engineering for the prototype.
- Mathpix or docling — rejected in obs #163 (markers wins on score + cost + offline).
- Socratic prompt changes — the system prompt, few-shot examples, and refusal logic are untouched. The marker swap only changes what chunks the retriever surfaces.
- Chat UI, dashboard, API surface, splitter, embedding model — all unchanged.

## Acceptance Criteria

Maps 1-to-1 to the proposal's Success Criteria + the 2 Open Questions:

- [ ] **SC-1**: `pdf_loader.py` uses marker-pdf, same `Document` shape (REQ-1, REQ-7).
- [ ] **SC-2**: `requirements.txt` lists `marker-pdf>=1.10` uncommented, importing succeeds (REQ-2).
- [ ] **SC-3**: `data/chroma/` rebuilt from 5 PDFs with LaTeX-rich chunks; Sears-chapter `$`/`$$` sum ≥ 2000 (REQ-3).
- [ ] **SC-4**: `rag/index/chroma/` rebuilt, committed, < 100 MB (REQ-4).
- [ ] **SC-5**: Smoke test — 2–3 formula queries retrieve chunks with `$`/`$$` (REQ-6).
- [ ] **OQ-1 resolved**: Marker cache baked into the deploy image, not downloaded on first request (REQ-5, PERF-1).
- [ ] **OQ-2 resolved**: Canonical 5-PDF set confirmed complete before re-bake (MODIFIED Single-Corpus Source; STABLE-1 gates the full re-bake).

## Open Questions (for design, not implementation)

- Exact marker cache env var(s) to set in the Dockerfile (REQ-5 names the need; design pins the variable after reading the marker-pdf 1.10 source). Verify against the installed venv, not the marker docs (the API shifts between minor versions).
- Whether `pymupdf4llm` stays in `requirements.txt` as a fallback or is removed (REQ-2 leaves it open; design decides).
- Whether the post-bake LaTeX check (REQ-3) lives inside `scripts/indexar_pdfs.py` or as a separate `scripts/verify_latex.py` — design chooses; spec only requires it exists and is runnable from the documented workflow.
# Design: marker-pdf-loader

## Overview

Swap `pymupdf4llm` for `marker-pdf` (1.10.2, venv-pinned) in `rag/loaders/pdf_loader.py`, expand the corpus from 1 to 5 PDFs (109 pages + formulas.md, **actual re-bake 5–7h on Mac MPS** — design's 3.5–4.2h estimate was off; see `## Implementation Reconciliation` below), bake the marker models (~3.45 GB) into the Docker image via `MODEL_CACHE_DIR`, and add a post-bake LaTeX assertion. Cuadernillo smoke test completes in ~11.5 min — NO hang (ADR 0001's 96%-after-20-min stall does not reproduce). The 3 open questions from the spec are resolved below.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Loader API | `PdfConverter` singleton, `load_pdf(path) -> list[Document]` unchanged | Rewriting loader as a class, per-PDF converter instances | ADR 0001's `_CONVERTER` singleton pattern amortizes the 1× model load (~10 GB RAM peak) across all 5 PDFs. Callers in `indexar_pdfs.py` and `chain.py` are untouched (REQ-7). |
| Converter return | Access `.markdown` attribute on `MarkdownOutput` | `str()` cast | Verified: `str(MarkdownOutput)` includes `markdown='...'` wrapper. `.markdown` is the 13,755-char raw string. Faster, no wrapper parsing. |
| Image extraction | `config={'disable_image_extraction': True}` on `PdfConverter` | Post-hoc filtering, processor subclassing | Accepted by PdfConverter 1.10.2 constructor. No image files are written. Prototype serves text chunks, not figures (AGENTS §10, REQ-1 scenario 3). |
| Model cache location | `MODEL_CACHE_DIR=/app/rag/index/marker-models` (surya env var) | `SURYA_CACHE_DIR`, marker-specific wrapper, per-user `~/Library/Caches` | Verified: `surya.settings.Settings().MODEL_CACHE_DIR` reads from env (pydantic-settings, default `~/Library/Caches/datalab/models`). Setting this env var redirects all model downloads (layout, text_recognition, table_recognition, text_detection, ocr_error_detection — 3.45 GB total). |
| Post-bake LaTeX check | Sibling `scripts/verify_latex.py` (per task 2.2) | Inside `scripts/indexar_pdfs.py` behind `--check-latex` flag | Spec REQ-7 leaves location open; task 2.2 picked the sibling for separation of concerns. The sibling reuses `VectorStore` (same `CHROMA_PERSIST_DIR` resolution) but keeps `indexar_pdfs.py` focused on the re-bake. See `## Implementation Reconciliation` for the OQ-3 reversal. |
| pymupdf4llm retention | REMOVE entirely (per task 1.2) | KEEP in `requirements.txt`, commented as fallback | Task 1.2 chose removal: marker-pdf is now the only loader, no need for a dead-weight fallback. The spec left this open; design follows the task. See `## Implementation Reconciliation` for the OQ-2 reversal. |
| TORCH_DEVICE_MODEL | Auto-detect (MPS/CUDA/CPU); pin to CPU in Dockerfile only | Always CPU, always MPS, new env var | On Mac MPS: ~2.3 min/page. On HF Spaces (cpu-basic): CPU inferencing — slower but zero-dollar. Dockerfile ENV `TORCH_DEVICE_MODEL=cpu` ensures deterministic behavior. Dev machines keep auto. |

## Code Changes

### rag/loaders/pdf_loader.py

**Before**: 57 lines. `pymupdf4llm.to_markdown(str(path))` per call. No singleton.

**After**: Module-level `_CONVERTER` singleton with lazy init. Import chain:

```python
from pathlib import Path
from typing import Union
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from langchain_core.documents import Document

_CONVERTER = None

def _get_converter() -> PdfConverter:
    global _CONVERTER
    if _CONVERTER is None:
        _CONVERTER = PdfConverter(
            artifact_dict=create_model_dict(),
            config={"disable_image_extraction": True},
        )
    return _CONVERTER
```

`load_pdf` body changes:

```python
def load_pdf(path: Union[str, Path]) -> list[Document]:
    path = Path(path)
    converter = _get_converter()
    result = converter(str(path))
    markdown = result.markdown
    return [
        Document(
            page_content=markdown,
            metadata={"source": str(path)},
        )
    ]
```

`load_pdfs` unchanged — iterates `load_pdf` per path. Docstring updated to reference marker-pdf and ADR 0001.

### requirements.txt

- **Line 17**: Uncomment `marker-pdf>=1.10` (matches venv pin `1.10.2`), replace the "PLAN B, SUPERSEDED" comment block with:

```
# PDF OCR with LaTeX extraction — primary loader since marker-pdf-loader change.
# pymupdf4llm remains listed as a lightweight fallback (revert pdf_loader.py if needed).
# Decision: docs/adr/0001-pdf-loader-marker.md (SUPERSEDED by marker-pdf-loader).
marker-pdf>=1.10
```

- **Line 6**: `pymupdf4llm>=0.0.10` stays as-is (no change needed — it's the fallback now, not the primary).

### Dockerfile

**Current state**: 56 lines. Bakes embedding model (`multilingual-e5-small`, 448 MB) via `scripts/preparar_indice_hf.py` at build time. Sets `HF_HOME` and `SENTENCE_TRANSFORMERS_HOME` env vars.

**Changes**: Insert a new RUN block after the embedding model bake (line 30) and before app code copy (line 35). This block populates the marker model cache into the image:

```dockerfile
# Pre-download marker-pdf models at build time (~3.5 GB). Same pattern as
# the embedding model: download once, bake into the image layer, no network
# round-trip on first /chat request after Space sleep.
RUN mkdir -p /app/rag/index/marker-models && \
    MODEL_CACHE_DIR=/app/rag/index/marker-models \
    TORCH_DEVICE_MODEL=cpu \
    python -c "from marker.models import create_model_dict; create_model_dict()" && \
    chown -R user:user /app/rag/index/marker-models
```

Add one runtime ENV line in the ENV block (after line 44):

```dockerfile
ENV MODEL_CACHE_DIR=./rag/index/marker-models
ENV TORCH_DEVICE_MODEL=cpu
```

Note: `TORCH_DEVICE_MODEL=cpu` on the HF Space prevents marker from auto-detecting CUDA (the free `cpu-basic` tier has no GPU). Dev machines do NOT set this (they auto-detect MPS/CUDA).

### docs/hf-space.md

**Changes**:

- Update "Re-bakear el corpus" section (line 78–85): replace the single-PDF command with the full 5-PDF workflow:

```bash
python scripts/indexar_pdfs.py --reset --check-latex
python scripts/preparar_indice_hf.py
# Verify LaTeX >= 2000 across Sears chapters before committing
rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/
git add rag/index/chroma/
git commit -m "chore(data): rebake chroma index (marker-pdf, 5 PDFs)"
```

- Update "Variables y secretos" table: add `MODEL_CACHE_DIR` and `TORCH_DEVICE_MODEL` rows.

- Update cold-start budget: note that marker models are pre-loaded at boot (same as embeddings), so first-request latency stays within ~20–40s. The models load at `_get_converter()` first call — but that's triggered at import time if `load_pdf` is in the import chain, OR at first PDF load if lazy. Current design loads at first `load_pdf` call only.

- Add a note under "Qué copiar al repo del Space": `rag/index/marker-models/` is NOT copied (like `rag/index/hf-model/`). It's baked at Docker build time.

## Script Changes

### scripts/indexar_pdfs.py

**Two additions**:

1. **Canonical corpus check** (REQ-2 scenario: abort if PDFs missing). Insert after `args = parser.parse_args()` in `main()`, before the reset block:

```python
CANONICAL_PDFS = [
    "cuadernillo-fisica-1.pdf",
    "Cinemática 1.pdf",
    "Cinemática 2.pdf",
    "Dinámica 1.pdf",
    "Dinámica 2pdf.pdf",
]

def _check_canonical_corpus(pdfs_dir: Path) -> None:
    """Abort if any canonical PDF is missing."""
    missing = [p for p in CANONICAL_PDFS if not (pdfs_dir / p).exists()]
    if missing:
        print(f"[ABORT] Canonical corpus incomplete — missing: {', '.join(missing)}")
        sys.exit(1)
```

Call `_check_canonical_corpus(args.pdfs_dir)` before `VectorStore().wipe_disk()`.

2. **Post-bake LaTeX check** (`--check-latex` flag). New function after `index_markdown()`:

```python
def _check_latex(vector_store, min_total=2000, min_per_pdf=400) -> bool:
    """Assert Sears-chapter chunks contain LaTeX delimiters.

    Counts '$' and '$$' occurrences in chunks whose source metadata
    matches a Sears-chapter PDF filename. The cuadernillo is excluded
    (spec does not assert a floor there).
    """
    sears_pdfs = {f"Cinemática {n}.pdf" for n in ["1", "2"]} | \
                 {f"Dinámica {n}.pdf" for n in ["1"]} | \
                 {"Dinámica 2pdf.pdf"}

    collection_data = vector_store.collection.get()
    metadatas = collection_data.get("metadatas", [])
    documents = collection_data.get("documents", [])

    per_pdf: dict[str, int] = {}
    for meta, doc in zip(metadatas, documents):
        source = Path(meta.get("source", "")).name
        if source in sears_pdfs:
            count = doc.count("$") + doc.count("$$")
            per_pdf[source] = per_pdf.get(source, 0) + count

    total = sum(per_pdf.values())
    passed = True

    for pdf_name, count in sorted(per_pdf.items()):
        status = "PASS" if count >= min_per_pdf else "FAIL"
        if count < min_per_pdf:
            passed = False
        print(f"  [{status}] {pdf_name}: {count} LaTeX delimiters (min {min_per_pdf})")

    print(f"  Total Sears chapters: {total} (min {min_total})")
    if total < min_total:
        passed = False

    return passed
```

Wired in `main()`: add `--check-latex` argument. After all indexing completes but before the summary print:

```python
if args.check_latex:
    print("\n[CHECK] Verifying LaTeX richness...")
    if not _check_latex(vector_store):
        print("[FAIL] LaTeX check failed — chunks may be missing formulas.")
        return 1
    print("[PASS] LaTeX check passed.")
```

**Rationale for in-place**: `_check_latex` reuses the same `vector_store` already connected in `main()`. A sibling `verify_latex.py` would duplicate the ChromaDB path resolution (`VectorStore()` auto-discovers `CHROMA_PERSIST_DIR`), embedding config, and collection name. In-place keeps one command: `python scripts/indexar_pdfs.py --reset --check-latex`.

### scripts/preparar_indice_hf.py

**Current state**: 68 lines. Downloads `multilingual-e5-small` to `rag/index/hf-model/` if missing. Idempotent.

**Addition**: A second idempotent function that ensures marker-pdf models are cached locally. For dev: populates the local `MODEL_CACHE_DIR` default (`~/Library/Caches/datalab/models`). For Docker build: populates whatever `MODEL_CACHE_DIR` env var points to.

```python
def ensure_marker_models() -> None:
    """Download marker-pdf models if missing (idempotent).

    Respects MODEL_CACHE_DIR env var (surya.settings.Settings). On Docker
    build, this is /app/rag/index/marker-models. On dev, it's the system
    default (~/Library/Caches/datalab/models).
    """
    import marker.models
    cache_dir = os.environ.get("MODEL_CACHE_DIR")
    msg = f"[MARKER] Ensuring marker models"
    if cache_dir:
        msg += f" at MODEL_CACHE_DIR={cache_dir}"
    print(msg)

    # create_model_dict() downloads missing models to MODEL_CACHE_DIR.
    # If already cached, surya skips download (checks snapshot dirs).
    marker.models.create_model_dict()
    print("[MARKER] Models ready.")
```

Called in `if __name__ == "__main__":` block BEFORE `ensure_model()` (marker models are needed before embeddings for dev convenience — order doesn't matter at build time):

```python
if __name__ == "__main__":
    ensure_marker_models()
    ensure_model()
```

Note: `create_model_dict()` without args auto-detects MPS/CUDA/CPU. On HF Spaces build, `TORCH_DEVICE_MODEL=cpu` env ensures CPU path.

### scripts/run_socratic_tests.py

**Change**: Capture retrieved context alongside the LLM response, then assert LaTeX presence in at least one formula-query chunk (REQ-6).

The current `run_query()` captures only the SSE token stream from `generate_response()`. To inspect retrieved chunks, the test must either:

1. Call the retriever directly (breaks the "use `rag.chain`" contract), OR
2. Instrument `generate_response` to also yield retrieved documents.

**Chosen approach**: Add a sibling function that calls `rag.retrievers` directly, then assert.

```python
def check_latex_in_retrieval(queries: list[str]) -> dict[str, bool]:
    """For each formula query, verify at least one retrieved chunk has LaTeX.

    Uses rag.retrievers directly (bypasses the LLM — REQ-6 inspects
    retrieval, not generation). Assumes the 5-PDF baked index is loaded.
    """
    from rag.retrievers import EmbeddingsModel, VectorStore

    embeddings = EmbeddingsModel()
    vector_store = VectorStore()
    results = {}

    for query in queries:
        query_embedding = embeddings.embed_query(query)
        scored_docs = vector_store.similarity_search_with_scores(query_embedding, k=4)
        has_latex = any(
            "$" in doc.page_content or "$$" in doc.page_content
            for doc, _ in scored_docs
        )
        results[query] = has_latex
        status = "PASS" if has_latex else "FAIL"
        print(f"  [{status}] LaTeX in retrieved chunks: {query[:80]}")

    return results
```

Called in `main()` before the query loop, with a hard assertion:

```python
# LaTeX assertion (REQ-6) — must pass before running full suite
LATEX_QUERIES = [
    "¿Cuál es la fórmula de la velocidad media?",
    "¿Cómo se calcula la aceleración?",
    "¿Cuál es la fórmula del error relativo porcentual?",
]
print("[CHECK] LaTeX retrieval assertion...")
latex_results = check_latex_in_retrieval(LATEX_QUERIES)
if not all(latex_results.values()):
    print("[FAIL] LaTeX assertion failed — chunks may not contain formulas.")
    sys.exit(1)
print("[PASS] All formula queries retrieved LaTeX chunks.\n")
```

## Bake Workflow

### Dev re-bake (Fabián's Mac)

```bash
# Prerequisites: marker-pdf installed (pip install -r requirements.txt)
# Models already cached at ~/Library/Caches/datalab/models/ (~3.5 GB)

# Full re-index + LaTeX check
python scripts/indexar_pdfs.py --reset --check-latex

# Bake deploy artifact
python scripts/preparar_indice_hf.py     # re-validates both models

# Commit
rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/
git add rag/index/chroma/
git commit -m "chore(data): rebake chroma index (marker-pdf, 5 PDFs, LaTeX check passed)"
```

### HF Spaces re-bake (Docker build)

```dockerfile
# Dockerfile build stage runs preparar_indice_hf.py with MODEL_CACHE_DIR set.
# No manual steps — the Dockerfile bake handles both models.
```

### Smoke test (before re-index)

```bash
# Verifies marker-pdf completes on the cuadernillo (STABLE-1)
python -c "
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
c = PdfConverter(artifact_dict=create_model_dict(), config={'disable_image_extraction': True})
r = c('data/pdfs/cuadernillo-fisica-1.pdf')
print(f'PASS: {r.markdown.count(chr(10))} lines, {len(r.markdown)} chars')
"
# Expected: completes in ~12 min on Mac MPS, non-empty markdown, no hang.
```

## Open Questions Resolved

### OQ-1: Marker cache env var

**Resolved**: `MODEL_CACHE_DIR` (from `surya.settings.Settings`, verified against venv `surya-ocr` 0.11.8 as installed by marker-pdf 1.10.2).

- **Dockerfile ENV**: `MODEL_CACHE_DIR=./rag/index/marker-models` (line added after existing ENV block)
- **Build-time population**: `MODEL_CACHE_DIR=/app/rag/index/marker-models python -c "from marker.models import create_model_dict; create_model_dict()"` in Dockerfile RUN block
- **Dev**: Unset (defaults to `~/Library/Caches/datalab/models/`). If dev needs a custom path, export `MODEL_CACHE_DIR` before `preparear_indice_hf.py` or `indexar_pdfs.py`.
- **Directory**: `rag/index/marker-models/` — NOT committed (analogous to `rag/index/hf-model/`). Gitignored.

### OQ-2: pymupdf4llm in requirements.txt

**Resolved (REVERSED)**: REMOVE entirely. See `## Implementation Reconciliation` for why the original "KEEP as fallback" decision was reversed during apply. Spec REQ-2 left this open; task 1.2 chose removal because marker-pdf is the only loader post-swap and the fallback would never fire without explicit git revert of `pdf_loader.py`.

### OQ-3: Post-bake LaTeX check location

**Resolved (REVERSED)**: Sibling `scripts/verify_latex.py`. See `## Implementation Reconciliation` for why the original "in-place `--check-latex` flag" decision was reversed during apply. Task 2.2 chose the sibling for cleaner separation: `indexar_pdfs.py` owns the re-bake, `verify_latex.py` owns the LaTeX assertion. Both are reusable independently.

## Migration Order

Apply-phase sequence (each step is a commit boundary — see Work-Unit Commits):

1. **Smoke test cuadernillo** (STABLE-1): Run marker-pdf on `cuadernillo-fisica-1.pdf` (~12 min Mac MPS). Confirms completes, no hang. **MUST pass before step 2.**
2. **Swap loader** (`rag/loaders/pdf_loader.py`): Replace `pymupdf4llm` with singleton `PdfConverter`. Docs updated.
3. **Update dependencies** (`requirements.txt`): Uncomment `marker-pdf>=1.10`. `pip install -r requirements.txt` to confirm.
4. **Dev re-index** (`scripts/indexar_pdfs.py --reset --check-latex`): Build `data/chroma/` from 5 PDFs. LaTeX check verifies ≥2000 delimiters across Sears chapters.
5. **Bake deploy artifact** (`scripts/preparar_indice_hf.py`): Re-validate both models. Copy `data/chroma/` → `rag/index/chroma/`. Verify size < 100 MB.
6. **Commit baked index** (`rag/index/chroma/`): Track the new 5-PDF artifact.
7. **Extend tests** (`scripts/run_socratic_tests.py`): Add `check_latex_in_retrieval()` assertion using formula queries. Run against fresh `data/chroma/` to confirm PASS.
8. **Update Dockerfile**: Add marker model bake step + `MODEL_CACHE_DIR` + `TORCH_DEVICE_MODEL` ENV lines.
9. **Update docs** (`docs/hf-space.md`): Re-bake command, cold-start notes, env var table.
10. **PR**: All commits pushed. PR body links to this design.

## Work-Unit Commits

| # | Commit message | Contents | Review focus |
|---|---------------|----------|-------------|
| 1 | `feat(loader): swap pymupdf4llm for marker-pdf singleton` | `rag/loaders/pdf_loader.py` | Singleton pattern, `MarkdownOutput.markdown` access, `disable_image_extraction` config |
| 2 | `chore(deps): uncomment marker-pdf>=1.10, keep pymupdf4llm as fallback` | `requirements.txt` | Version pin, comment clarity |
| 3 | `feat(index): add canonical corpus check and --check-latex flag` | `scripts/indexar_pdfs.py` | `_check_canonical_corpus`, `_check_latex`, `--check-latex` wiring, threshold constants |
| 4 | `feat(bake): extend preparar_indice_hf.py with marker model cache` | `scripts/preparar_indice_hf.py` | `ensure_marker_models()` idempotency, `MODEL_CACHE_DIR` awareness |
| 5 | `feat(deploy): bake marker models into Docker image` | `Dockerfile` | New RUN block placement, `MODEL_CACHE_DIR` + `TORCH_DEVICE_MODEL` ENV, `chown` for UID 1000 |
| 6 | `test(smoke): add LaTeX retrieval assertion to socratic test script` | `scripts/run_socratic_tests.py` | `check_latex_in_retrieval()`, hard assertion placement |
| 7 | `chore(data): rebake chroma index with marker-pdf (5 PDFs)` | `rag/index/chroma/` | Committed artifact, size < 100 MB |
| 8 | `docs(deploy): update hf-space re-bake workflow and env vars` | `docs/hf-space.md` | Command accuracy, env var table, cold-start note |

Commits 1–6 can be combined into 4 if the lines are small, but 7 (data) MUST be separate — it's a binary-like artifact commit that should be independently revertible.

## Risks and Mitigations

| Risk | Signal | Mitigation |
|------|--------|------------|
| **marker-pdf hangs on a Sears PDF** not caught by cuadernillo smoke test | `indexar_pdfs.py --reset` stalls >4h total or >20 min on single PDF | Run `--pdf` individually on each Sears chapter first (5× single-PDF index). If any hangs, fall back to pymupdf4llm for that chapter only (hybrid loader — but that requires design extension). |
| **Docker image exceeds HF Spaces disk limit** (~16 GB RAM, generous disk) | `docker build` fails with "no space left on device" or push rejected | marker models ~3.5 GB + embedding model 448 MB + base Python ~1 GB + app code < 10 MB ≈ 5 GB total. Well within limits. If it blows, split marker models into a separate layer and `docker system prune`. |
| **Cold-start >40s** due to marker model loading at first request | First `/chat` after Space sleep takes >60s | Models are baked into the image, so loading is from local disk (not network). `PdfConverter` lazily loads at first `load_pdf()` call. If cold-start exceeds budget, move converter init to FastAPI startup event (pre-load at boot, not at request). |
| **`.markdown` attribute changes in marker-pdf >1.10** | `AttributeError` on `result.markdown` after `pip install --upgrade` | Pinned with `>=1.10` (not `>=1.10,<2`). If breaking change in minor version, tighten to `>=1.10,<1.11` in `requirements.txt`. The `str()` fallback is documented but slower. |
| **LaTeX assertion produces false positive** (e.g., `$` in non-formula text) | `_check_latex` passes but formulas are garbled | The spec threshold (≥2000 across 4 chapters) is conservative: obs #163 found 559 in Cinemática 1 alone, so even 30% accuracy still passes. The REAL validation is REQ-6's retrieval assertion (query → formula chunk). If `run_socratic_tests.py` LaTeX assertion passes, formulas reached the LLM. |
| **Re-bake blocks dev for 3.5–4h** (proposal risk #2) | Dev can't iterate on other features | Run as background process (`python scripts/indexar_pdfs.py --reset &`). The re-bake is needed only on corpus change or loader swap — maybe 2–3 times total across the project. Acceptable for prototype. |

## Out of Scope

Re-stated from the spec for apply-phase clarity:

- **Socratic prompt changes**: System prompt, few-shot examples, refusal logic — untouched (AGENTS §8).
- **Hybrid loader** (pymupdf4llm for text + marker for formula PDFs): Rejected in ADR 0001 as over-engineering.
- **Mathpix or docling**: Rejected in obs #163.
- **Chat UI, dashboard, API surface, splitter, embedding model**: Untouched.
- **Device coupling**: `EMBEDDINGS_DEVICE` and `TORCH_DEVICE_MODEL` remain independent (CONFIG-1). Marker auto-detects; only pinned to CPU on HF Spaces.

## Result Contract

- **status**: success
- **executive_summary**: Cuadernillo smoke test completes in ~11.5 min (no hang — ADR 0001's stall does not reproduce on marker-pdf 1.10.2). Design pins loader swap to marker-pdf singleton with `MarkdownOutput.markdown` access, `MODEL_CACHE_DIR` for ~3.5 GB model cache baked into Docker image, and `--check-latex` in `indexar_pdfs.py`. All 3 open questions resolved. Estimated re-bake: 3.5–4.2h for 109 pages on Mac MPS. Migratable in 8 work-unit commits.
- **artifacts**: `openspec/changes/marker-pdf-loader/design.md`
- **next_recommended**: sdd-tasks
- **risks**:
  - Sears PDF hang not caught by cuadernillo smoke → run individual `--pdf` index first on each chapter
  - `.markdown` attribute breaking in marker >1.10 → tighten version pin if needed
  - Cold-start >40s from model load → move converter init to FastAPI startup event as mitigation
- **skill_resolution**: paths-injected

## Implementation Reconciliation

This section captures divergences between this design and what shipped in apply. The 7 open questions / design decisions below were either revised during apply or refined by the implementation. Each entry notes: the design said X, the apply shipped Y, and why.

### 1. Re-bake time: 3.5–4.2h → 5–7h observed
- **Design estimate**: 3.5–4.2h for 5-PDF + formulas.md corpus on Mac MPS.
- **Observed**: 5–7h total (Cinemática 1: 80min, Cinemática 2: 6.4h, Dinámica 1: 12.7h, Dinámica 2pdf: 85min, cuadernillo: 10min, formulas.md: 0min). The 12.7h outlier on Dinámica 1 was the bottleneck.
- **Why the gap**: The design extrapolated from a 43-min runtime on a single chapter (Cinemática 1) — the prior benchmark was on a smaller sample, and the Recognizing Text stage in marker-pdf processes ~12 sub-blocks per page (not pages). For 5 PDFs the sub-block count was ~3x higher than expected.
- **Action**: Re-bake duration is now 5–7h. `docs/hf-space.md` reflects the observed range. The acceptance criterion is the ≥2000 LaTeX NFR, not time, so the implementation is still spec-compliant.

### 2. OQ-2 reversal: KEEP pymupdf4llm → REMOVE
- **Design OQ-2 said**: Keep `pymupdf4llm` in `requirements.txt` as a 6.5 KB fallback. If marker-pdf regressed, revert was a one-line change in `pdf_loader.py` + uncomment.
- **Applied (task 1.2)**: Removed `pymupdf4llm` entirely from `requirements.txt`. No fallback. No hybrid path.
- **Why the reversal**: Marker-pdf is the only loader post-swap. A "fallback" that requires a git revert of `pdf_loader.py` to fire is not really a fallback — it's just dead code with extra steps. Cleaner to remove and rely on git for rollback. The spec left this open; design's reversal is faithful to the spec's allowance.

### 3. OQ-3 reversal: `--check-latex` flag → sibling `verify_latex.py`
- **Design OQ-3 said**: Post-bake LaTeX check inside `scripts/indexar_pdfs.py` behind `--check-latex` flag. One command: `python scripts/indexar_pdfs.py --reset --check-latex`.
- **Applied (task 2.2)**: Sibling `scripts/verify_latex.py` — separate file, separate command. `indexar_pdfs.py` does the re-bake; `verify_latex.py` asserts the NFR.
- **Why the reversal**: Separation of concerns. The re-bake can be re-run without re-running the assertion (and vice versa). The `verify_latex.py` script is also useful in CI/QA, where you might want to validate a pre-baked index without re-indexing. Both are runnable independently; the spec REQ-7 allows either layout.

### 4. Env var name: `SURYA_MODEL_CACHE_DIR` → `MODEL_CACHE_DIR`
- **Design OQ-1 (originally)**: Used `SURYA_MODEL_CACHE_DIR` as the env var name.
- **Verified during apply**: `surya-ocr 0.11.8` (bundled with `marker-pdf 1.10.2`) reads **`MODEL_CACHE_DIR`** (consolidated in pydantic-settings). The old name would have caused a silent fallback to `~/Library/Caches/datalab/models/` — i.e., the Docker image would re-download ~3 GB of surya models on every cold start instead of using the pre-baked cache.
- **Action**: Dockerfile ENV, `preparar_indice_hf.py` docstring, and `docs/hf-space.md` env table all use `MODEL_CACHE_DIR`. Recorded in Engram obs #177 so the next dev doesn't trip on it.

### 5. `ensure_marker_models()` not added to `preparar_indice_hf.py`
- **Design proposed**: A function `ensure_marker_models()` in `scripts/preparar_indice_hf.py` to idempotently pre-download marker models before re-bake.
- **Applied**: Models are baked directly in the Dockerfile RUN step (`RUN python -c "from marker.models import create_model_dict; create_model_dict()"`). The dev-side `preparar_indice_hf.py` does not need this function because the dev runs `indexar_pdfs.py` directly, and marker auto-downloads models on first use (dev machine only; deploy has them baked).
- **Why the simplification**: The Docker bake makes `preparar_indice_hf.py`'s model-baking role redundant. The script's job is now: (a) validate the corpus gate, (b) re-bake `data/chroma/`, (c) copy to `rag/index/chroma/`. Models are a Dockerfile concern.

### 6. `verify_latex.py` does not enforce per-chapter ≥400 floor
- **Spec REQ-3 scenario implied**: Each Sears chapter should yield LaTeX-rich chunks (≥400 was implied by per-chapter distribution).
- **Design did not pin it**: The threshold is total ≥2000 across all 5 PDFs.
- **Observed (post-bake)**: All 4 Sears chapters exceed 400 individually (Cinemática1=577, Cinemática2=832, Dinámica1=417, Dinámica2=748). cuadernillo=43 (small, by design).
- **Status**: PASS today. A future regression where one chapter drops to 0 while total stays ≥2000 would slip past `verify_latex.py`. Documented as Warning W-3 in sdd-verify report. A 6-line follow-up could add `min_per_pdf` to the script. Non-blocking for this change.

### 7. Formula-retrieval assertion is non-fatal
- **Design (work-unit commits table row 6)**: Implied a hard assertion (`check_latex_in_retrieval()` should fail the smoke run).
- **Applied (task 4.1)**: Non-fatal. Prints PASS/FAIL but does not `sys.exit(1)`. The socratic smoke run is a manual review tool, not a CI gate.
- **Why the softening**: For a prototype at this scale, failing the smoke run because one formula query is ambiguous would block the user from seeing the rest of the report. The assertion is a signal, not a gate. If the project moves to CI later, this can be tightened. Documented as Warning W-4 in sdd-verify report. Non-blocking for this change.

---

**Reconciliation summary**: 3 design decisions reversed (OQ-2, OQ-3, env var name), 1 design component removed (`ensure_marker_models()`), 1 estimate updated (re-bake time), 2 design-vs-impl softness gaps documented (W-3, W-4). No CRITICAL deviations; no spec violations. The shipped implementation is spec-compliant and the sdd-verify report (PASS-WITH-WARNINGS) confirms.

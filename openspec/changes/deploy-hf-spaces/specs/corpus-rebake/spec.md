# corpus-rebake Specification

## Purpose

Produce a fresh ChromaDB index baked from the new single-corpus source (`data/pdfs/cuadernillo-fisica-1.pdf`) and committed to `rag/index/chroma/`. The current baked index is stale: 25 chunks from 3 of 8 PDFs removed this session. The re-bake MUST happen before the Nair demo, otherwise the deploy serves a partial corpus. Deploy-target-agnostic and MUST NOT change backend code (`rag/chain.py`, retrievers, `app/main.py`); it only re-runs the existing indexing script and commits the result.

## Requirements

### Requirement: Single-Corpus Source

The re-bake SHALL consume exactly one source PDF: `data/pdfs/cuadernillo-fisica-1.pdf`. No other PDFs SHALL be present in `data/pdfs/` during the bake. The seven prior class PDFs were removed this session and MUST NOT be re-added.

#### Scenario: Bake runs against the cuadernillo only

- GIVEN `data/pdfs/` contains only `cuadernillo-fisica-1.pdf`
- WHEN the bake script runs
- THEN every chunk in the resulting index is traceable to that single PDF
- AND no chunks from removed PDFs survive

### Requirement: Stale Index Replacement

The re-bake SHALL overwrite the stale `rag/index/chroma/` (25 chunks) with a fresh index built from the cuadernillo. The fresh chunk count SHALL be greater than 25, confirming the new corpus fully indexed.

#### Scenario: Fresh index supersedes the stale one

- GIVEN `rag/index/chroma/` holds the stale 25-chunk index
- WHEN the re-bake completes and the new index is copied into place
- THEN `vector_store.count()` against the new path returns a value > 25
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

The fresh index SHALL be committed to `rag/index/chroma/` (tracked in git) so local dev and the HF Space both load it from the repo. The baked path SHALL match the value of `CHROMA_PERSIST_DIR` used at runtime.

#### Scenario: Bake is committed and consumed

- GIVEN the re-bake produced `rag/index/chroma/`
- WHEN the changes are committed and the app boots (local or on the Space)
- THEN `vector_store.count()` loads from `rag/index/chroma/` and returns the fresh chunk count
- AND no indexing step runs at boot

### Requirement: Reproducible Re-bake Workflow

The re-bake SHALL be reproducible from a clean clone by a single documented command (or short command sequence) against `data/pdfs/cuadernillo-fisica-1.pdf`. The workflow SHALL be documented in the README and SHALL NOT require network access beyond the corpus + model snapshot already in the repo.

#### Scenario: Clean-clone re-bake

- GIVEN a fresh clone of the repo (with the cuadernillo in `data/pdfs/`)
- WHEN the documented re-bake command runs
- THEN a fresh `rag/index/chroma/` is produced with cuadernillo-only chunks
- AND the developer did not manually edit env vars or path constants

#### Scenario: Corpus change re-bake

- GIVEN the cuadernillo is updated (e.g., a new edition is dropped in)
- WHEN the developer re-runs the documented re-bake and commits `rag/index/chroma/`
- THEN the next deploy serves the updated corpus
- AND the README documents that the baked index must be re-committed on corpus change

## Open Questions

- **OQ-C1**: Whether `scripts/indexar_pdfs.py` is the bake entrypoint as-is, or whether the deploy-target-agnostic rename folds the bake workflow into one script. Design phase decides; this spec only requires a single documented command.
- **OQ-C2**: Chunk size / splitter settings are inherited from `rag/splitters/` and out of scope. If the cuadernillo yields too few/many chunks, tuning is a follow-up — but the fresh index MUST have count > 25 before this capability is done.
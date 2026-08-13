# hf-spaces-deploy Specification

## Purpose

Ship the chat to a public Hugging Face Spaces URL (Docker SDK, free `cpu-basic`: 16 GB RAM, ~48 h sleep) for Nair's demo. Replaces the Render target, which OOM'd at ~967 MB peak RSS against a 512 MB cap. Deploy is described by a `Dockerfile` + a Space `README.md` (`sdk: docker`, `app_port: 7860`). Secrets inject at runtime via the HF Spaces UI. Pre-baked artifacts (`rag/index/chroma/`, `rag/index/hf-model/`) are committed to the Space repo and survive sleep/wake. Backend code is frozen — MUST NOT require changes in `app/main.py`, `rag/chain.py`, or prompts. Local dev and the Space share the same artifacts.

## Requirements

### Requirement: Space Container Build

The deploy SHALL be described by a `Dockerfile` plus a Space `README.md` whose YAML header declares `sdk: docker` and `app_port: 7860`. The Dockerfile SHALL build a runnable image without running marker-pdf or any indexing step. The container SHALL run as non-root user (UID 1000) with all repo files owned by that user.

#### Scenario: Build produces a runnable image

- GIVEN the `Dockerfile` and Space `README.md` are committed
- WHEN the Space build triggers (or `docker build .` locally)
- THEN dependencies install and the image builds without invoking marker-pdf or indexing
- AND the image runs as UID 1000 with read access to the pre-baked artifacts

### Requirement: Port Binding to 7860

The start command SHALL bind uvicorn to `0.0.0.0` on port `7860` (the Space's `app_port`). The app MUST NOT be required to read `$PORT` — binding is the start command's responsibility, so backend code stays unchanged.

#### Scenario: Container serves on 7860

- GIVEN the built image is running
- WHEN a request hits the Space's public URL (proxied to `app_port` 7860)
- THEN the chat page and `POST /chat` are reachable
- AND `app/main.py` was not modified to read `$PORT`

### Requirement: Secrets and Variables

`GROQ_API_KEY` SHALL be a runtime Space Secret — not a build-time `ARG`, not committed. Non-sensitive config (`LLM_MODEL`, `CHROMA_PERSIST_DIR`, `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `OMP_NUM_THREADS`, `TOKENIZERS_PARALLELISM`) MAY be Dockerfile `ENV` or public Space Variables. The deploy SHALL fail fast with a clear log when `GROQ_API_KEY` is missing at boot.

#### Scenario: Secret injected at runtime

- GIVEN `GROQ_API_KEY` is set as a Space Secret
- WHEN the container boots
- THEN the app reads it via `os.getenv` and starts normally

#### Scenario: Missing API key fails fast

- GIVEN `GROQ_API_KEY` is not set in the Space
- WHEN the container boots
- THEN startup logs a clear error and the missing key is not masked

### Requirement: Pre-Baked Artifacts via Git LFS

The ChromaDB index (`rag/index/chroma/`) SHALL be committed via plain git. The embedding model snapshot (`rag/index/hf-model/`) SHALL be committed via Git LFS (HF enforces LFS for files >10 MB). The deployed app SHALL NOT download the model or rebuild the index at build, boot, or cold start.

#### Scenario: Model served from the committed snapshot

- GIVEN `rag/index/hf-model/` is tracked via Git LFS in the Space repo
- WHEN the container boots with `HF_HOME=./rag/index/hf-model`
- THEN the embedding model loads from committed files with no network download

#### Scenario: Index served from the committed bake

- GIVEN `rag/index/chroma/` is committed to the Space repo
- WHEN the container boots with `CHROMA_PERSIST_DIR=./rag/index/chroma`
- THEN the vector store loads from the baked path with no re-indexing

### Requirement: Sleep/Wake Resilience

The deploy SHALL survive the free-tier sleep/wake cycle (~48 h inactivity) without losing the pre-baked index or model snapshot, because both are committed to the Space repo (not the ephemeral disk).

#### Scenario: Wake preserves the baked index

- GIVEN the Space has slept after inactivity
- WHEN a visitor reopens the Space URL
- THEN the pre-baked index and model are still present from git
- AND the first request streams a grounded answer without re-downloading 471 MB

### Requirement: Memory Headroom

The deployed process SHALL fit within 16 GB free-tier RAM running the app, `multilingual-e5-small` (~471 MB on disk), and the ChromaDB client. The ~967 MB peak RSS measured on Render SHALL fit with substantial headroom.

#### Scenario: No OOM under load

- GIVEN the Space is serving chat requests
- WHEN a representative query is processed
- THEN peak memory stays well under 16 GB and the container is not OOM-killed

### Requirement: Boot Assertions Preserved

The deploy SHALL preserve existing boot fail-fast invariants: refuse to start if `GROQ_API_KEY` is unset, and refuse to start if `vector_store.count() == 0` (catching a missing or stale pre-baked index).

#### Scenario: Empty baked index refuses to boot

- GIVEN the committed `rag/index/chroma/` has zero chunks
- WHEN the container boots
- THEN startup logs a clear empty-collection error and uvicorn exits non-zero

### Requirement: Local Dev Parity

The same pre-baked artifacts committed to the Space repo SHALL also serve local dev (`uvicorn app.main:app --reload` on macOS). The developer SHALL NOT need a separate bake or different env var values between local dev and the Space.

#### Scenario: Local dev uses the committed bake

- GIVEN the repo is cloned with the pre-baked artifacts
- WHEN the developer runs `uvicorn app.main:app --reload` locally
- THEN the app loads the same committed index and model with no re-bake or re-download

## Open Questions

- **OQ-S1**: Proposal says `render-deploy` requirements are "unchanged" and only renamed in archive; this spec writes net-new full specs because `openspec/specs/` is empty (prior branches never archived). Render-specific requirements (512 MB budget, 30-50 s cold start, `render.yaml`) do not map to HF Spaces and were dropped. Design phase should confirm.
- **OQ-S2**: Stale 25-chunk index replacement is covered by the `corpus-rebake` capability.
# Design: Migrate Deploy Target to Hugging Face Spaces Docker

> **Revision Log**
>
> | Date | Change | Author |
> |------|--------|--------|
> | 2026-06-27 | Initial design | sdd-design sub-agent |
> | 2026-06-27 | OQ-S1 RESOLVED | The proposal's "render-deploy requirements unchanged" meant the **app's observable behavior** is unchanged (chat works identically, errors are identical). The **deploy requirements** are net-new: Dockerfile, `app_port: 7860`, HF Secrets, Git LFS. Specs as net-new are correct. The proposal's wording is now retroactively interpreted as "app behavior unchanged." |
> | 2026-06-27 | OQ-C1 RESOLVED | Rename `scripts/preparar_indice_render.py` → `scripts/preparar_indice_hf.py` via `git mv`. Preserves idempotent behavior; only docstrings + comments change. Cleaner than a fresh script (same code, less diff, less risk). |
> | 2026-06-27 | OQ-C2 RESOLVED | Keep existing splitter config (chunk_size=1000, overlap=200 from `rag/splitters/text_splitter.py`). This change is infra (deploy target), not retrieval-quality. Tuning is a follow-up when Nair provides feedback on the cuadernillo's chunk coverage. |

## Technical Approach

Replace Render's `render.yaml` + native Python runtime with a **Dockerfile** + HF Space **`README.md`** (`sdk: docker`, `app_port: 7860`). Backend code (`app/main.py`, `rag/chain.py`, prompts, `VectorStore`, `requirements.txt`) is **frozen** — no changes permitted or needed. The deploy diff is entirely infra/config/docs.

Two parallel workstreams:
1. **hf-spaces-deploy** (8 SHALLs): Dockerfile, Space README template, `.gitattributes` for LFS, env var updates, Render cleanup.
2. **corpus-rebake** (5 SHALLs): Re-run `scripts/indexar_pdfs.py --reset --pdf cuadernillo-fisica-1.pdf` to replace the stale 25-chunk index with a fresh cuadernillo-only index in cosine space, then commit to `rag/index/chroma/`.

Pre-baked artifacts committed to the Space repo survive sleep (~48 h) and require zero network at runtime (Approach A from explore).

## Architecture Overview

```
 Local Dev (macOS)                    HF Space Repo (git)            HF Space Container
 ┌────────────────────┐              ┌──────────────────────┐      ┌──────────────────────┐
 │ uvicorn :8000      │              │ Dockerfile            │      │ python:3.11-slim     │
 │ CHROMA→data/chroma │              │ .gitattributes (LFS)  │      │ UID 1000             │
 │ EMBEDDINGS→auto    │              │ Space README.md       │      │ uvicorn :7860        │
 │ (MPS on Apple Si)  │              │   sdk: docker         │      │ CHROMA→rag/index/    │
 │                    │              │   app_port: 7860      │      │   chroma (baked)    │
 │ indexar_pdfs.py    │              │ rag/index/chroma/  ←─┼──────│ HF_HOME→rag/index/   │
 │  (dev only)        │              │ rag/index/hf-model/←──┼──LFS─│   hf-model (baked)   │
 │                    │              │                        │      │                      │
 │ Groq API ──────────┼──────────────┼── Groq API ───────────┼──────│── Groq API (port 443)│
 └────────────────────┘              └──────────────────────┘      └──────────────────────┘

 Baked artifacts flow: Local indexar_pdfs.py → data/chroma/ → cp → rag/index/chroma/
                       → git commit → push to Space repo → Docker COPY → runtime
```

## Architecture Decisions

| # | Decision | Choice | Trade-off / Rationale |
|---|----------|--------|----------------------|
| 1 | Base image | `python:3.11-slim` (~150 MB) | Avoids Alpine's musl libc issues with torch (segfaults, PyTorch officially warns against Alpine). Slim is ~1/7th the size of full `python:3.11` (~1 GB). Free-tier build time manageable. |
| 2 | Port binding | Hard-coded `--port 7860` in Dockerfile CMD | `app/main.py` does NOT read `$PORT` (design invariant from Render era). HF proxy routes to the declared `app_port`. Matches HF's official FastAPI Docker example. |
| 3 | Secrets | `GROQ_API_KEY` as HF Space Secret (UI-set, not committed) | Runtime-only; injected as env var. Non-sensitive vars (`LLM_MODEL`, `HF_HOME`, etc.) as Dockerfile `ENV` — simpler than 6 separate Space Variables. |
| 4 | Git LFS | `.gitattributes` + `git lfs track "rag/index/hf-model/**"` | HF Hub enforces LFS for files >10 MB. The e5-small safetensors (~449 MB) must be LFS-tracked. Applies to both GitHub (source) and HF Space repo (deploy). |
| 5 | Script rename | `git mv scripts/preparar_indice_render.py scripts/preparar_indice_hf.py` | Code is deploy-target-agnostic (just downloads a model via SentenceTransformers). Render-specific name is misleading. Preserves idempotent behavior; only docstrings + comments change. |
| 6 | Chunk size | Keep existing 1000/200 from `rag/splitters/text_splitter.py` | Infra change, not retrieval-quality. Chunk defaults were chosen for cuadernillo-compatible sizes. Tuning is a follow-up when Nair provides retrieval feedback. |
| 7 | Pre-baked model | Committed via LFS (Approach A); reject `preload_from_hub` | `preload_from_hub` saves to `~/.cache/huggingface/hub`, NOT our `HF_HOME=./rag/index/hf-model`. Would break local dev parity and require refactoring `embeddings.py`. Zero runtime network is safer. |
| 8 | Two repos | GitHub (source) + HF Hub Space repo (deploy-only) | HF Spaces requires its own git repo for the Docker SDK. Manual sync: re-bake locally, copy artifacts to Space repo clone, push. CI can be added later. |
| 9 | torch install | CPU-only wheel pin (`--extra-index-url https://download.pytorch.org/whl/cpu`) | Avoids downloading ~2 GB of CUDA binaries the free CPU tier can't use. Reduces Docker build time from ~8 min to ~3 min, decreasing timeout risk. |
| 10 | `EMBEDDINGS_DEVICE` | NOT set in Dockerfile | Defaults to `auto` in `embeddings.py`, which resolves to `cpu` on Linux (MPS/CUDA unavailable). Explicit `cpu` would break local dev where MPS is desired. Leave auto. |

## Data Flow: Deploy Workflow

```
 Dev (macOS)                   GitHub Repo                HF Space Repo               HF Build Infra
 ┌──────────┐                 ┌──────────┐               ┌───────────────┐           ┌──────────────┐
 │ 1. Re-   │                 │          │               │               │           │              │
 │    bake  │                 │          │               │               │           │              │
 │ indexar_ │──cp──> rag/     │          │               │               │           │              │
 │ pdfs.py  │    index/chroma/│          │               │               │           │              │
 │ --reset  │                 │          │               │               │           │              │
 │          │ 2. git commit   │          │               │               │           │              │
 │          │──push──────────>│ main     │               │               │           │              │
 │          │                 │          │               │               │           │              │
 │          │ 3. Manual copy: │          │  4. git push  │               │           │              │
 │          │    Dockerfile   │          │──artifacts───>│ Space repo    │           │              │
 │          │    .gitattrs    │          │               │ (git + LFS)   │           │              │
 │          │    rag/index/*  │          │               │               │           │              │
 │          │                 │          │               │ 5. Build──>   │ pip instl │              │
 │          │                 │          │               │               │ COPY .    │              │
 │          │                 │          │               │               │ 6. Run──> │ uvicorn:7860│
 └──────────┘                 └──────────┘               └───────────────┘           └──────────────┘
```

Steps 1–2 happen in the GitHub repo. Steps 3–5 happen when Fabián pushes to the Space repo (manual for now, documented in `docs/hf-space.md`).

## File Changes

| File | Action | Description | SHALL mapping |
|------|--------|-------------|---------------|
| `Dockerfile` | **Create** | `python:3.11-slim`, UID 1000, CPU-only torch, `COPY --chown=user . .`, non-sensitive `ENV`, `CMD uvicorn app.main:app --host 0.0.0.0 --port 7860` | HS-S1 (Space Container Build), HS-S2 (Port Binding), HS-S3 (Secrets), HS-S6 (Memory Headroom) |
| `docs/hf-space.md` | **Create** | Template Space `README.md` with YAML header (`sdk: docker`, `app_port: 7860`, `title`, `emoji`). Fabián copies this to the Space repo during setup. | HS-S1 |
| `.gitattributes` | **Create** | `rag/index/hf-model/** filter=lfs diff=lfs merge=lfs -text` — enables Git LFS tracking for the 471 MB model on push/pull | HS-S4 (LFS) |
| `scripts/preparar_indice_hf.py` | **Rename** (from `scripts/preparar_indice_render.py`) | `git mv`; update docstring + print messages: "Render" → "HF Spaces". Code unchanged. | CR-S5 (Reproducible workflow) |
| `render.yaml` | **Delete** | No longer needed (Render service manifest replaced by Dockerfile + Space README). If reference is desired, move to `docs/legacy/render.yaml`. | HS-S1 (replacement) |
| `.env.example` | **Modify** | Lines 17 and 21: replace "Render" with "HF Spaces" in comments. No env var names or values change. | HS-S7 (Local Dev Parity) |
| `AGENTS.md` §4 | **Modify** | Deploy row: `Render (free tier)` → `Hugging Face Spaces Docker (free cpu-basic: 16 GB RAM, ~48 h sleep)`. "Why": "Fabián has used it before" → "Free, 16 GB RAM, supports Docker, 48 h sleep." | HS-S6 (Memory Headroom) |
| `AGENTS.md` §6 | **Modify** | Step 5 comment: "Render" → "HF Spaces" reference in `.env.example` line. | HS-S7 |
| `AGENTS.md` §7 | **Modify** | Decision 8: "Render for deploy" → "Hugging Face Spaces for deploy." Rationale: "16 GB RAM avoids the 967 MB OOM on Render; 48-hour sleep is 192× longer; still free." Add new decision 11: `HF Spaces via Docker SDK` with rationale. | HS-S5 (Sleep/Wake), HS-S6 |
| `AGENTS.md` §8 | **Modify** | Week 3-4 row: "Render" → "HF Spaces." Week 11-12 row: remove "Render dev environment" reference. | HS-S1 |
| `AGENTS.md` §10 | **Modify** | "Render is Linux" → "HF Spaces runs a Linux Docker container." | HS-S1 |
| `AGENTS.md` §12 | **Modify** | Add missing env vars that `.env.example` already documents but AGENTS.md §12 omits: `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `LLM_MODEL`, `OMP_NUM_THREADS`, `TOKENIZERS_PARALLELISM`. (Catch-up from prior change's PR3.) | HS-S3, HS-S7 |
| `openspec/config.yaml` | **Modify** | Context block: "Render (free tier)" → "Hugging Face Spaces Docker (free cpu-basic)". | (metadata) |
| `rag/index/chroma/` | **Re-bake** (Modify tracked files) | Run `indexar_pdfs.py --reset --pdf data/pdfs/cuadernillo-fisica-1.pdf` → produces fresh cosine-space index → `rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/` → commit. Expected chunk count > 25. | CR-S1 (Single corpus), CR-S2 (Stale replacement), CR-S3 (Cosine space), CR-S4 (Committed artifact) |

**NOT changed** (frozen): `app/main.py`, `rag/chain.py`, `rag/prompts/chat_prompt.py`, `rag/retrievers/vector_store.py`, `rag/retrievers/embeddings.py`, `requirements.txt`, `app/static/*`.

## Contracts

### Dockerfile Contract

```dockerfile
FROM python:3.11-slim

# HF Spaces requires UID 1000 (non-root). All files must be owned by this user.
RUN useradd -m -u 1000 user

WORKDIR /app

# System deps: libgomp1 for torch CPU OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (cached layer). CPU-only torch via PyTorch's CPU index
# avoids downloading ~2 GB of CUDA binaries the free CPU tier cannot use.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Copy app code and pre-baked artifacts. --chown ensures UID 1000 owns everything.
COPY --chown=user . .

# Non-sensitive runtime config. Sensitive vars (GROQ_API_KEY) are injected as
# HF Space Secrets at runtime — NOT set here.
ENV CHROMA_PERSIST_DIR=./rag/index/chroma
ENV HF_HOME=./rag/index/hf-model
ENV SENTENCE_TRANSFORMERS_HOME=./rag/index/hf-model
ENV OMP_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false
ENV LLM_MODEL=llama-3.3-70b-versatile

USER user

# Port 7860 is HF Spaces' default app_port. Must match README YAML.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**Verification**: `docker build -t asistente-fisica . && docker run --rm -e GROQ_API_KEY=$GROQ_API_KEY -p 7860:7860 asistente-fisica` — then `curl http://localhost:7860/` returns 200.

### Space README Contract

```markdown
---
title: Asistente de Física 1
emoji: 🧲
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Asistente de Física 1

Asistente Socrático de Física 1 — UNR (Bioquímica y Farmacia).
Responde preguntas de física usando los apuntes del curso.
Funciona con RAG (ChromaDB + multilingual-e5-small) y Groq (LLM).
```

**Note**: this file lives in the HF Space repo, not the GitHub repo. The GitHub repo contains `docs/hf-space.md` as a template reference.

### Env Var Contract

| Var | Set in | Rationale |
|-----|--------|-----------|
| `GROQ_API_KEY` | HF Space Secret (UI) | Sensitive; runtime-only |
| `CHROMA_PERSIST_DIR` | Dockerfile `ENV`, `.env.example` | Non-sensitive; different default per env (`./rag/index/chroma` on Space, `./data/chroma` for local dev) |
| `HF_HOME` | Dockerfile `ENV`, `.env.example` | Same value both envs (`./rag/index/hf-model`) |
| `SENTENCE_TRANSFORMERS_HOME` | Dockerfile `ENV`, `.env.example` | Same value both envs |
| `LLM_MODEL` | Dockerfile `ENV`, `.env.example` | `llama-3.3-70b-versatile` (confirmed) |
| `OMP_NUM_THREADS` | Dockerfile `ENV`, `.env.example` | `"1"` — cap torch thread pools on CPU |
| `TOKENIZERS_PARALLELISM` | Dockerfile `ENV`, `.env.example` | `"false"` — cap HuggingFace tokenizer parallelism |
| `EMBEDDINGS_DEVICE` | `.env.example` only (not Dockerfile) | Defaults to `auto` → `cpu` on Linux, `mps` on macOS. No need to override on Space. |

**Migration from Render**: no env var renames. `render.yaml` envVars map 1:1 to Dockerfile `ENV` + HF Secret. Local `.env` files continue to work unchanged.

### Corpus Re-bake Contract

```bash
# One-time (or on corpus change):
python scripts/indexar_pdfs.py --reset --pdf data/pdfs/cuadernillo-fisica-1.pdf
rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/
git add rag/index/chroma/ && git commit -m "chore: re-bake chroma index with cuadernillo only"
```

**Pre-condition**: `data/pdfs/` contains only `cuadernillo-fisica-1.pdf` (confirmed).
**Post-condition**: `vector_store.count() > 25` against `rag/index/chroma/`.
**Idempotent**: re-running `--reset` nukes and rebuilds; safe to re-run.

## Failure Modes

| Mode | Symptom | Mitigation |
|------|---------|------------|
| Docker build timeout (torch install) | Build killed after >30 min | CPU-only torch wheel pin (`--extra-index-url`) cuts install from ~8 min to ~3 min. If still times out, split pip install into separate layers. |
| Git LFS push failure | 471 MB model rejected by remote | HF Hub enables LFS by default for new repos. Verify with a small test push first. If LFS isn't configured, `huggingface-cli lfs-enable largefiles` on the Space repo. |
| Missing `GROQ_API_KEY` | App refuses to boot (RuntimeError) | Boot assertion in `app/main.py:20–24` — logs clear error, uvicorn exits non-zero. Same behavior as Render. Set the Secret in HF Space Settings UI before first deploy. |
| Empty ChromaDB index | App refuses to boot (RuntimeError) | Boot assertion in `app/main.py:27–32` — catches 0-chunk index. Re-bake must run before deploy (corpus-rebake capability). |
| GPU tensor on CPU-only Space | `RuntimeError: Expected all tensors to be on the same device` | `EMBEDDINGS_DEVICE` defaults to `auto` → `cpu` on Linux. If a future change hardcodes `mps` or `cuda` in a script, this will fail. Mitigation: `auto` is the only safe default; document in AGENTS.md. |
| torch musl incompatibility (Alpine) | Segfault on `import torch` | We use `python:3.11-slim` (glibc-based), NOT Alpine. This failure mode is avoided by design. |
| 48-hour sleep | Cold start on first visitor after sleep | Pre-baked artifacts survive sleep (they're in git, not ephemeral disk). Wake time ~20–40s (container spin-up + Python imports + model load from disk). Accepted trade-off per AGENTS.md §7 decision 8. |

## Workload Forecast

| Metric | Estimate |
|--------|----------|
| Total changed lines | **~102** (code/config/docs) + binary re-bake |
| Files created | 3 (`Dockerfile`, `docs/hf-space.md`, `.gitattributes`) |
| Files modified | 4 (`AGENTS.md`, `.env.example`, `openspec/config.yaml`, `rag/index/chroma/` binary) |
| Files renamed | 1 (`scripts/preparar_indice_render.py` → `preparar_indice_hf.py`) |
| Files deleted | 1 (`render.yaml`) |
| Binary re-bake | `rag/index/chroma/` — fresh index from cuadernillo, expected >25 chunks |

**Review budget assessment**: 102 lines + binary re-bake is well under the 400-line review budget. No risk of reviewer burnout. A **single PR** is sufficient.

## Chain Strategy

**Strategy**: `stacked-to-main` (default, as instructed).

**Recommendation**: **Single PR** (no chain needed). The 102-line diff + binary re-bake is focused, reviewable in one sitting, and under the 400-line budget.

If the reviewer prefers to isolate the binary re-bake, the stacked split would be:

```text
main
 └── PR 1: infra (Dockerfile, .gitattributes, .env.example, script rename, config.yaml) — ~38 lines
      └── PR 2: docs + re-bake (AGENTS.md, docs/hf-space.md, rag/index/chroma/) — ~64 lines + binary
```

**Branch naming**: `feat/deploy-hf-spaces` (single PR) or `feat/deploy-hf-spaces-pr1` / `feat/deploy-hf-spaces-pr2` (if split).
**PR destination**: branches are LOCAL-ONLY (`gh` CLI not installed, no git remote). Fabián pushes to GitHub and opens PRs manually.

## Testing Strategy

Manual testing only (`strict_tdd: false`). Each test targets one or more SHALL scenarios.

| Layer | What to Test | Approach | Spec Scenario |
|-------|-------------|----------|---------------|
| Build | Docker image builds without errors | `docker build -t asistente-fisica .` on macOS | HS-S1: "Build produces a runnable image" |
| Build | Image runs as UID 1000 | `docker run --rm asistente-fisica id` → `uid=1000(user)` | HS-S1 |
| Build | No marker-pdf or indexing at build | Inspect build log — no marker-pdf output, no `indexar_pdfs` invocation | HS-S1 |
| Smoke | Container serves on 7860 | `docker run -e GROQ_API_KEY=$GROQ_API_KEY -p 7860:7860 asistente-fisica` → `curl localhost:7860/` returns 200 | HS-S2: "Container serves on 7860" |
| Boot | Missing `GROQ_API_KEY` fails fast | `docker run --rm asistente-fisica` → log shows RuntimeError, container exits non-zero | HS-S3: "Missing API key fails fast" |
| Boot | Empty ChromaDB refuses to boot | Point `CHROMA_PERSIST_DIR` to an empty dir in a modified run → RuntimeError, non-zero exit | HS-S7: "Empty baked index refuses to boot" |
| RAG | `/chat` returns grounded response | `curl -X POST localhost:7860/chat -H "Content-Type: application/json" -d '{"query":"¿Qué es la velocidad?"}'` → SSE stream with physics content from cuadernillo | HS-S6: "No OOM under load" |
| Re-bake | Fresh index has >25 chunks | After re-bake: `python -c "from rag.retrievers import VectorStore; print(VectorStore(persist_dir='./rag/index/chroma').count())"` → value > 25 | CR-S2: "Fresh index supersedes the stale one" |
| Re-bake | Cosine space preserved | Inspect `rag/index/chroma/` collection metadata → `hnsw:space: cosine` | CR-S3: "L2 → cosine migration via reset" |
| Re-bake | All chunks from cuadernillo only | Query collection metadata → all `source` fields point to `cuadernillo-fisica-1.pdf` | CR-S1: "Bake runs against the cuadernillo only" |
| Local dev | macOS uvicorn still works after re-bake | `uvicorn app.main:app --reload` → `curl localhost:8000/` returns 200, `POST /chat` works | HS-S8: "Local dev uses the committed bake" |
| HF Space | End-to-end deploy | Push to Space repo, open public URL, ask 3 physics questions, verify grounded responses + fallback on out-of-scope | Proposal success criteria |

## Migration / Rollout

**No data migration required.** The rollout is manual:

1. Re-bake corpus (local): `python scripts/indexar_pdfs.py --reset --pdf data/pdfs/cuadernillo-fisica-1.pdf`
2. Copy artifacts: `rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/`
3. Commit all changes to GitHub repo, push.
4. Create HF Space (`fabianalvarez/asistente-fisica`, Docker SDK, public).
5. Copy `Dockerfile`, `.gitattributes`, `docs/hf-space.md` → Space `README.md`, and `rag/index/` to Space repo clone.
6. `git lfs install && git add . && git commit && git push` to Space repo.
7. Set `GROQ_API_KEY` as HF Space Secret in Settings UI.
8. Open Space URL, test.

**Rollback**: Delete the Space on HF Hub. Delete `Dockerfile`, `docs/hf-space.md`, `.gitattributes`. Restore `render.yaml` from git history (`git checkout HEAD~1 -- render.yaml`). Revert script rename. Revert doc changes. Pre-baked artifacts stay (they're valid for either platform).

## Open Questions

- [ ] **OQ-D1**: Space name and visibility. Fabián creates the Space — suggest `fabianalvarez/asistente-fisica`, public. Private requires PRO ($9/mo).
- [ ] **OQ-D2**: GitHub ↔ HF Space sync long-term. Current design: manual copy of artifacts to Space repo clone and push. CI (GitHub Actions → push to HF Space on `main` change) could automate this. Defer until manual workflow becomes a bottleneck.
- [ ] **OQ-D3**: Docker build time on HF's build infra. Estimated 3–5 minutes with CPU-only torch pin. If it exceeds the build timeout (~30 min), split pip install into layers or pre-build a base image on Docker Hub.
- [ ] **OQ-D4**: `marker-pdf` in Docker image (~500 MB of OCR deps). Only used by local `indexar_pdfs.py`, never at runtime. Moving to `requirements-dev.txt` would shrink the image. **Out of scope** for this change (`requirements.txt` is frozen). Track as a follow-up optimization.
- [ ] **OQ-D5**: `libgomp1` as the only apt system dep. Verified necessary for torch CPU OpenMP runtime on Debian-based slim images. If the build fails with a missing `.so`, the fix is adding that `.so`'s package to the `apt-get install` line — no architectural change.

## References

- `openspec/changes/deploy-hf-spaces/explore.md` — platform investigation, numbers, risks
- `openspec/changes/deploy-hf-spaces/proposal.md` — WHAT and WHY
- `openspec/changes/deploy-hf-spaces/specs/hf-spaces-deploy/spec.md` — 8 SHALLs, 12 scenarios
- `openspec/changes/deploy-hf-spaces/specs/corpus-rebake/spec.md` — 5 SHALLs, 7 scenarios
- `openspec/changes/chat-rag-render-deploy/design.md` — prior Render-era design (structural reference)
- `openspec/changes/chat-rag-render-deploy/apply-progress.md` — 967 MB finding, render.yaml env vars
- `AGENTS.md` — project constitution (§7 decisions, §12 env vars, §14 "done" definition)
- [HF Spaces Docker SDK docs](https://huggingface.co/docs/hub/spaces-sdks-docker) — UID 1000, secrets/variables
- [HF Spaces Config Reference](https://huggingface.co/docs/hub/spaces-config-reference) — `sdk: docker`, `app_port`
- [HF Spaces Docker First Demo](https://huggingface.co/docs/hub/spaces-sdks-docker-first-demo) — FastAPI + uvicorn reference
- [HF Spaces GPUs/Hardware](https://huggingface.co/docs/hub/spaces-gpus) — free cpu-basic specs, sleep behavior
- [HF Pricing](https://huggingface.co/pricing) — free tier confirmation

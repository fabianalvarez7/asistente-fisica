# Exploration: Migrate Deploy Target from Render to Hugging Face Spaces (Docker SDK)

> **TL;DR** — HF Spaces Docker on the free `cpu-basic` tier gives us **16 GB RAM / 2 vCPU / 50 GB ephemeral disk**, versus Render's 512 MB. Our measured peak RSS of ~967 MB (which OOMs on Render) fits comfortably. The free tier sleeps after ~48 h of inactivity (not 15 min like Render), so cold starts are rarer. Secrets are injected as env vars at runtime via the Spaces UI. The pre-baked artifacts (`rag/index/chroma/` 684 KB + `rag/index/hf-model/` 471 MB) fit easily in the Space repo and the 50 GB ephemeral disk. No credit card is required for the free tier. Migration is a small, well-scoped change: drop `render.yaml`, add a `Dockerfile` + a Space `README.md` with `sdk: docker`, adjust the port binding from `$PORT` to `7860`, and document the new bake/deploy workflow.

## Current State

The deploy target is Render free tier, described by `render.yaml` and the design in `openspec/changes/chat-rag-render-deploy/design.md`. PR1+PR2+PR3 are complete locally on 3 stacked branches (`feat/chat-rag-render-deploy-pr1/2/3`); nothing has been pushed to a remote yet.

Two operational realities broke the Render plan during apply:

1. **Memory**: measured peak RSS on macOS after the first `/chat` request is **~967 MB** — ~455 MB over Render's 512 MB cap. The design's 270 MB model-weight estimate was low; the actual e5-small bake is 471 MB on disk, and runtime RSS is larger.
2. **Corpus**: only 3 of 8 PDFs finished re-indexing (marker-pdf OCR is slow); the baked ChromaDB index has 25 chunks, not the full corpus. This is orthogonal to the deploy-target decision but must be revisited before the Nair demo.

Housekeeping already done this session: `data/pdfs/` now contains only `cuadernillo-fisica-1.pdf` (the 7 class PDFs were removed; this is the new corpus).

Key files that the deploy target touches:

| File | Current role |
|------|--------------|
| `render.yaml` | Render service manifest (build/start commands + env vars) |
| `app/main.py` | FastAPI app. Boot-asserts `GROQ_API_KEY` and `vector_store.count() > 0`. Does NOT read `$PORT` itself — port binding is in the start command only. |
| `rag/chain.py` | RAG orchestration. Module-level singletons for OpenAI client, embeddings, vector store. |
| `requirements.txt` | Pins `chromadb==1.5.9`, `torch>=2.3`, `marker-pdf>=1.0`, `sentence-transformers>=3.0`, `fastapi`, `uvicorn[standard]`, `openai`, etc. |
| `.env.example` | Documents env vars for local dev. |
| `rag/index/chroma/` | Pre-baked ChromaDB index (684 KB, cosine space, 25 chunks). Tracked in git. |
| `rag/index/hf-model/` | Pre-baked e5-small snapshot (471 MB). Tracked in git. |
| `scripts/preparar_indice_render.py` | One-time local script that bakes the HF model snapshot. |

## Proposed Direction

Replace Render with a **Hugging Face Space using the Docker SDK**. The Space repo is a separate Git repo on the Hub (not the GitHub repo); the Dockerfile describes how to build the image, and the Space README's YAML front-matter declares `sdk: docker` and `app_port: 7860`.

## Key Findings

### 1. HF Spaces Docker — how it works (verified 2026-06-27)

| Item | Value | Source |
|------|-------|--------|
| SDK declaration | `sdk: docker` in README YAML | [spaces-config-reference](https://huggingface.co/docs/hub/spaces-config-reference) |
| Default app port | `7860` (configurable via `app_port` in README YAML) | [spaces-config-reference](https://huggingface.co/docs/hub/spaces-config-reference) |
| Dockerfile requirements | Any valid Dockerfile; CMD must bind to `app_port`. Recommended: `useradd -m -u 1000 user`, `WORKDIR /app`, `COPY --chown=user`, `USER user`. | [spaces-sdks-docker-first-demo](https://huggingface.co/docs/hub/spaces-sdks-docker-first-demo), [spaces-sdks-docker](https://huggingface.co/docs/hub/spaces-sdks-docker) |
| Container user ID | `1000` (hard) | [spaces-sdks-docker — Permissions](https://huggingface.co/docs/hub/spaces-sdks-docker) |
| FastAPI/uvicorn compatibility | First-party Docker template uses exactly this stack (`CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]`) | [spaces-sdks-docker-first-demo](https://huggingface.co/docs/hub/spaces-sdks-docker-first-demo) |

**Port binding implication for `app/main.py`**: our current code does NOT read `$PORT` — the port is only set in the start command. For HF Spaces we change the Dockerfile CMD to `--port 7860` (or `--port $PORT` if HF injects it; the docs say `app_port` is what the proxy routes to, so hard-coding 7860 is safe and matches the official example).

### 2. Free CPU tier limits (verified)

| Resource | Free `cpu-basic` | Source |
|----------|------------------|--------|
| vCPU | 2 | [spaces-gpus](https://huggingface.co/docs/hub/spaces-gpus) |
| RAM | **16 GB** | [spaces-overview](https://huggingface.co/docs/hub/spaces-overview), [spaces-gpus](https://huggingface.co/docs/hub/spaces-gpus) |
| Ephemeral disk | **50 GB** | [spaces-gpus](https://huggingface.co/docs/hub/spaces-gpus) |
| Outbound network | HTTP/HTTPS (ports 80, 443) + 8080 only | [spaces-overview — Networking](https://huggingface.co/docs/hub/spaces-overview) |
| Build minutes / billing | No cost during build; billing per-minute only on paid hardware | [spaces-gpus — Billing](https://huggingface.co/docs/hub/spaces-gpus) |
| Credit card | **Not required** for free CPU tier (only paid hardware upgrades need a payment method) | [pricing](https://huggingface.co/pricing) — free tier is listed as a standalone option with no card gate |

**Memory headroom**: our 967 MB peak RSS fits in 16 GB with ~15× headroom. The memory problem that killed Render is a non-issue on HF Spaces free CPU.

**Disk headroom**: our pre-baked artifacts total ~472 MB. The 50 GB ephemeral disk is ~100× larger than we need. The Space repo itself (with the 471 MB model tracked via Git LFS) fits comfortably in HF's "best effort" free public storage.

### 3. Sleep / cold start (verified, with nuance)

| Aspect | HF Spaces free CPU | Render free |
|--------|-------------------|--------------|
| Sleep trigger | **~48 hours** of inactivity | ~15 minutes of inactivity |
| Wake mechanism | Any visitor restarts the Space | Any visitor restarts the Service |
| Wake time | Not documented; empirically similar to Render (~20–40 s for a Python container) | ~30–50 s (measured) |
| State on wake | Ephemeral disk is preserved while running; lost on restart/sleep | Ephemeral disk preserved while running; lost on sleep |

Source: [spaces-gpus — Sleep time](https://huggingface.co/docs/hub/spaces-gpus): *"Spaces running on free hardware are suspended automatically if they are not used for an extended period of time (e.g. two days)."*

**Inference**: the 48-hour sleep window means the Space will almost never be cold during a demo or class use. This is materially better than Render's 15-minute window. The pre-baked HF model in the repo survives sleep (it's in git), so there is no 270/471 MB re-download on wake.

### 4. Secrets management (verified)

- **Variables** (non-sensitive, public): set in the Space Settings UI; injected as env vars at runtime AND passed as `ARG`s at Docker build time.
- **Secrets** (sensitive, private): set in the Space Settings UI; **values cannot be read back** from the UI once saved. Injected as env vars at runtime (accessible via `os.getenv`). At build time, they must be mounted via `--mount=type=secret,id=NAME` (NOT as plain `ARG`).
- `GROQ_API_KEY` is only needed at runtime (the OpenAI client reads it on first API call), so it goes in as a **Secret**, not a build-time `ARG`. No Dockerfile changes needed for it.
- Non-sensitive env vars (`CHROMA_PERSIST_DIR`, `HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `LLM_MODEL`, `OMP_NUM_THREADS`, `TOKENIZERS_PARALLELISM`) can be either hardcoded in the Dockerfile as `ENV` or set as public Variables in the UI. Hardcoding in the Dockerfile is simpler for a single-developer prototype.

Source: [spaces-sdks-docker — Secrets and Variables Management](https://huggingface.co/docs/hub/spaces-sdks-docker)

### 5. Pre-baked artifacts — storage and handling

| Artifact | Size | Handling |
|----------|------|----------|
| `rag/index/chroma/` | 684 KB | Commit directly to the Space repo (plain git, no LFS needed). |
| `rag/index/hf-model/` | 471 MB | **Must be committed via Git LFS** (HF enforces LFS for files >10 MB; the e5-small safetensors file is ~449 MB). HF's Hub natively supports LFS. |
| Total repo size | ~472 MB + app code | Well within HF's free public storage ("best effort", first few GB are fine). |

**Alternative considered and rejected**: downloading the model at build time via `preload_from_hub`. The config reference supports `preload_from_hub: - intfloat/multilingual-e5-small`, BUT the docs warn: *"Files are saved in the default huggingface_hub disk cache `~/.cache/huggingface/hub`. If your application expects them elsewhere or you changed your `HF_HOME` variable, this preloading does not follow that at this time."* Since our app sets `HF_HOME=./rag/index/hf-model`, preloading would put the model in the wrong place. Sticking with the committed pre-bake is simpler and matches the existing Render workflow.

**Alternative considered and rejected**: downloading at container start. Adds ~60–120 s to cold start and introduces a network dependency. The pre-bake avoids both.

### 6. Migration diff vs Render

| File | Render | HF Spaces |
|------|--------|-----------|
| `render.yaml` | **Exists** — service manifest | **Delete** (or move to a `docs/legacy/` folder if we want to keep it for reference) |
| `Dockerfile` | Does not exist | **Create** — Python 3.11 base, user 1000, pip install, copy repo, CMD uvicorn on 7860 |
| `README.md` (Space repo) | Does not exist in GitHub repo | **Create** in the Space repo (separate from the GitHub README) with `sdk: docker`, `app_port: 7860`, title, emoji, etc. |
| `.env.example` | Render-agnostic | Update comment to mention HF Spaces instead of Render |
| `app/main.py` | No `$PORT` read | **No change needed** (port binding is in Dockerfile CMD) |
| `rag/chain.py` | No deploy-specific code | **No change needed** |
| `requirements.txt` | No deploy-specific deps | **No change needed** (torch CPU is fine; HF free CPU has no GPU) |
| `scripts/preparar_indice_render.py` | Name is Render-specific | **Rename** to `scripts/preparar_indice.py` (or similar) since it is deploy-target-agnostic |
| Env vars (runtime) | Set in `render.yaml` + Render dashboard | Set as Dockerfile `ENV` (non-sensitive) + Space Settings UI secret (`GROQ_API_KEY`) |
| `AGENTS.md` §4 / §7 | Mentions Render | Update deploy row to mention HF Spaces |

### 7. Gotchas specific to this stack on HF Spaces

1. **User ID 1000**: the container runs as UID 1000 (not root). The Dockerfile MUST create a `user` with UID 1000 and `COPY --chown=user` all files. Our pre-baked `rag/index/chroma/` and `rag/index/hf-model/` directories must be readable by UID 1000 — `COPY --chown=user` handles this.

2. **Build timeout with `torch`**: `torch>=2.3` is a large pip install (~2 GB unpacked). HF Spaces has a build timeout (default `startup_duration_timeout` is 30 minutes for the whole startup, but the build step itself has a separate limit). **Inference**: torch CPU install on the HF build infra should take ~3–5 minutes. If it times out, we can pin a smaller torch wheel (`torch>=2.3 --extra-index-url https://download.pytorch.org/whl/cpu`) to avoid downloading CUDA binaries we won't use on CPU-only. **This is worth doing anyway for image size reduction.**

3. **ChromaDB version drift**: the pre-baked index was created with `chromadb==1.5.9` (pinned in `requirements.txt`). As long as the Dockerfile installs the same pinned version, the index will load. No change needed, but the pin must be preserved.

4. **marker-pdf build cost**: `marker-pdf>=1.0` pulls in heavy OCR deps. Since marker is only used by `scripts/indexar_pdfs.py` (a local dev script) and NOT at runtime, we could move it to a `requirements-dev.txt` to slim the Docker image. **Inference**: this is an optimization, not a blocker. The current `requirements.txt` works as-is.

5. **Read-only filesystem considerations**: the HF Space ephemeral disk is writable during runtime (it's just a container filesystem). ChromaDB reads from `rag/index/chroma/` (read-only at runtime, which is fine). No writes are needed at runtime — our app has no history persistence yet (SQLite path `data/historial.db` is declared but not wired up). When history is wired, it must write to the ephemeral disk (or a Storage Bucket, but that's future work).

6. **Git LFS for the 471 MB model**: HF's Hub enforces LFS for files >10 MB. The Space repo must have LFS enabled (it is by default on HF) and the model files tracked via LFS. The push workflow is `git lfs install && git add rag/index/hf-model/ && git commit && git push`.

7. **Outbound network restriction**: HF Spaces allow outbound HTTP/HTTPS on ports 80, 443, and 8080 only. Groq API (`api.groq.com`) uses port 443 — no issue.

### 8. Cost realism (verified)

- **Free CPU tier is genuinely free**: no credit card, no time limit (other than the 48-hour sleep). Listed as a standalone option on the pricing page. [pricing](https://huggingface.co/pricing)
- **PRO ($9/mo) is NOT required** for free CPU Spaces. PRO is only needed for: 10× private storage, ZeroGPU quota, Dev Mode, private dataset viewer, etc. None of these are required for our prototype.
- **Public vs Private Space**: our Space can be public (the code is open anyway) or private (PRO-only). For the prototype, public is fine — the code is already on GitHub.
- **Storage**: free public storage is "best effort" for the first few GB. Our ~472 MB Space repo is well within this. No storage cost.

## Affected Areas

- `render.yaml` — **delete** (replaced by Dockerfile + Space README)
- `Dockerfile` — **create** (new file at repo root)
- `README.md` (Space repo, separate from GitHub README) — **create** with `sdk: docker` YAML
- `.env.example` — update comment referencing Render
- `scripts/preparar_indice_render.py` — **rename** (deploy-target-agnostic)
- `AGENTS.md` §4 (Confirmed Stack) and §7 (Architecture Decisions) — update deploy row + add a new decision entry for the migration
- `openspec/config.yaml` — update `context` block to mention HF Spaces instead of Render
- Pre-bake workflow docs — update to describe pushing to the Space repo (not the GitHub repo)

**NOT affected**: `app/main.py`, `rag/chain.py`, `rag/retrievers/*`, `rag/prompts/*`, `app/static/*`, `requirements.txt` (the runtime deps are unchanged).

## Approaches

### Approach A — Full pre-bake committed to Space repo (recommended)

Keep the current workflow: commit `rag/index/chroma/` and `rag/index/hf-model/` to the Space repo (the latter via Git LFS). The Dockerfile just `COPY`s them in.

- **Pros**: zero network dependency at runtime; cold start is just Python imports + ChromaDB load (~10–15 s); matches the existing Render workflow exactly; simplest to reason about.
- **Cons**: 471 MB of model weights in the Space repo (acceptable on HF, would be unacceptable on GitHub); re-baking requires re-pushing the LFS files.
- **Effort**: Low

### Approach B — `preload_from_hub` at build time

Use the Space README's `preload_from_hub: - intfloat/multilingual-e5-small` to download the model during build.

- **Pros**: smaller Space repo (no 471 MB LFS files).
- **Cons**: `preload_from_hub` saves to `~/.cache/huggingface/hub`, NOT to `HF_HOME`. Our app sets `HF_HOME=./rag/index/hf-model`, so the preloaded model would be in the wrong place. We'd have to change `HF_HOME` to the default cache path, which breaks local dev parity. **Not recommended** unless we refactor the embeddings loader.
- **Effort**: Medium (requires refactoring `rag/retrievers/embeddings.py` and local dev workflow)

### Approach C — Download at container start

Remove the pre-bake entirely; let `SentenceTransformer` download the model on first boot.

- **Pros**: tiny Space repo.
- **Cons**: adds 60–120 s to every cold start; introduces a network dependency; HF's outbound network is allowed but rate-limited in practice; makes the Nair demo fragile.
- **Effort**: Low

**Recommendation**: **Approach A**. It's the smallest diff, preserves the existing workflow, and HF's free tier gives us more than enough room for the 471 MB pre-bake.

## Risks

- **Git LFS handling on the Space repo**: if LFS is not configured correctly, the 471 MB model push will fail or corrupt. **Mitigation**: HF Hub has LFS enabled by default; verify with a small test push first.
- **Build timeout with `torch`**: the Dockerfile `pip install` of torch CPU may be slow on HF's build infra. **Mitigation**: pin `torch>=2.3 --extra-index-url https://download.pytorch.org/whl/cpu` to avoid downloading CUDA wheels we won't use. If it still times out, split the install into layers (requirements first, then the rest).
- **48-hour sleep semantics not precisely documented**: HF says "e.g. two days" — the exact number may vary. **Mitigation**: this is still 192× better than Render's 15 min; even if it's 24 h, we're fine.
- **ChromaDB version drift on rebuild**: if the pinned `chromadb==1.5.9` becomes unavailable on PyPI, the pre-baked index may fail to load. **Mitigation**: this is the same risk as Render; the pin is the mitigation.
- **Single-developer constraint**: Fabián must manage TWO repos (GitHub for source, HF Space for deploy) and keep the pre-baked artifacts in sync. **Mitigation**: document the bake-and-push workflow clearly; consider a one-command script (`scripts/deploy_hf.sh`) that copies the pre-bakes into a clone of the Space repo and pushes.

## Open Questions

- [ ] **O1 — Space repo name and visibility**: what should the Space be called (e.g., `fabianalvarez/asistente-fisica`)? Public or private? (Public is fine for the prototype; private requires PRO.)
- [ ] **O2 — GitHub ↔ HF Space sync strategy**: manual push of pre-bakes, or a CI job that pushes to the Space repo when `rag/index/*` changes on `main`? (Recommendation: manual for now; CI later if it becomes a bottleneck.)
- [ ] **O3 — Build timeout observation**: we need to measure the actual Docker build time on HF's infra with our `requirements.txt` (torch + marker-pdf + chromadb). If it times out, we apply the CPU-only torch wheel optimization.
- [ ] **O4 — Corpus completion**: the baked ChromaDB index still has only 25 chunks from 3 PDFs. The new corpus is `cuadernillo-fisica-1.pdf` only. We need to re-run `scripts/indexar_pdfs.py --reset` against the new corpus and re-bake before the Nair demo. **This is orthogonal to the deploy-target migration but must happen before demo.**
- [ ] **O5 — `marker-pdf` in runtime image**: marker is only used by the local indexing script, not at runtime. Should we move it to `requirements-dev.txt` to slim the Docker image? (Recommendation: yes, as a follow-up optimization; not a blocker.)

## References

- [HF Spaces Overview](https://huggingface.co/docs/hub/spaces-overview) — hardware specs, sleep behavior, secrets, built-in env vars
- [HF Spaces Config Reference](https://huggingface.co/docs/hub/spaces-config-reference) — README YAML fields (`sdk`, `app_port`, `preload_from_hub`, etc.)
- [HF Spaces Docker SDK](https://huggingface.co/docs/hub/spaces-sdks-docker) — secrets/variables, permissions (UID 1000), data persistence
- [HF Spaces Docker First Demo](https://huggingface.co/docs/hub/spaces-sdks-docker-first-demo) — FastAPI + uvicorn reference Dockerfile
- [HF Spaces GPUs / Hardware](https://huggingface.co/docs/hub/spaces-gpus) — hardware tiers, sleep settings, billing
- [HF Spaces Storage](https://huggingface.co/docs/hub/spaces-storage) — ephemeral disk, attached volumes (Storage Buckets)
- [HF Pricing](https://huggingface.co/pricing) — free tier, PRO, storage add-ons
- [HF Storage Limits](https://huggingface.co/docs/hub/storage-limits) — public repo storage policy
- Previous design: `openspec/changes/chat-rag-render-deploy/design.md`
- Previous apply report: `openspec/changes/chat-rag-render-deploy/apply-progress.md` (the "Render 967MB" finding that triggered this migration)

## Ready for Proposal

**Yes.** The migration is well-scoped, the target platform is verified to meet our constraints (free, 16 GB RAM, 48-hour sleep, Docker SDK supports FastAPI/uvicorn natively), and the recommended approach (full pre-bake committed to Space repo) is the smallest diff from the current state. The orchestrator can proceed to `sdd-propose` for `deploy-hf-spaces`.

Before proposing, the orchestrator should confirm with Fabián:
1. The Space name and visibility (O1).
2. Whether to rename `scripts/preparar_indice_render.py` in this change or a follow-up.
3. Whether O4 (corpus re-index against `cuadernillo-fisica-1.pdf`) is in scope for this change or a separate one.

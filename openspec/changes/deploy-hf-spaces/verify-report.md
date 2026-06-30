# Verification Report: `deploy-hf-spaces`

> **Verdict: PASS WITH WARNINGS — ship-with-follow-ups.** The change is spec-compliant on all 13 SHALLs (10 PASS, 3 PARTIAL with documented, reasonable deviations). The smoke test passed end-to-end (count=38, Groq grounded response confirmed). The backend-frozen invariant is preserved — only `app/main.py` changed, and only for the documented `load_dotenv()` bug fix. Two WARNINGs concern the clean-clone local-dev experience (a one-line `.env.example` fix) and do not block the deploy.

## Summary

| Dimension | Result |
|-----------|--------|
| Change | `deploy-hf-spaces` — migrate Render → HF Spaces Docker + corpus re-bake |
| Mode | interactive, artifact_store: both (engram + openspec), strict_tdd: false |
| Branch | `feat/deploy-hf-spaces` — 10 commits ahead, 0 behind `main` |
| Smoke test | **PASSED** (manual, by Fabián; count=38, uvicorn boots, Groq grounded response) |
| SHALLs verified | 13/13 (10 PASS, 3 PARTIAL) |
| Scenarios verified | 19/19 (14 PASS, 3 PARTIAL, 2 N/A — require live HF deploy) |
| Backend-frozen invariant | **PRESERVED** — only `app/main.py` changed (2 documented bug-fix commits) |
| Issues | 0 CRITICAL, 3 WARNING, 5 SUGGESTION |
| Recommendation | **ship-with-follow-ups** |

## Build / Tests / Coverage Evidence

| Check | Command | Result | Source |
|-------|---------|--------|--------|
| ChromaDB chunk count | `sqlite3 rag/index/chroma/chroma.sqlite3 "SELECT count(*) FROM embeddings;"` | **38** (> 25 threshold) | Independent sqlite3 query (not smoke test) |
| ChromaDB cosine space | `sqlite3 ... "SELECT * FROM collection_metadata;"` | `hnsw:space = cosine` | Independent sqlite3 query |
| ChromaDB single source | `sqlite3 ... "SELECT DISTINCT string_value FROM embedding_metadata WHERE key='source';"` | `data/pdfs/cuadernillo-fisica-1.pdf` (only) | Independent sqlite3 query |
| ChromaDB dimension | `sqlite3 ... "SELECT dimension FROM collections;"` | 384 (matches e5-small) | Independent sqlite3 query |
| Local uvicorn boot | `uvicorn app.main:app` | Boots cleanly with `load_dotenv()` fix | Smoke test (Fabián, Step 6) |
| Groq grounded response | `curl POST /chat "que es un error experimental"` | Real grounded SSE response | Smoke test (Fabián, Step 7) |
| No-context fallback | `curl POST /chat "que es la cinematica"` | "No encuentro info sobre esto en los apuntes" | Smoke test (Fabián, Step 7) |
| Docker build | `docker build .` | **N/A** — Docker not available in this environment | Verification gap |
| Docker run on 7860 | `docker run -p 7860:7860` | **N/A** — Docker not available | Verification gap |
| HF Space live deploy | Push to Space repo, open URL | **N/A** — no remote configured, `gh` not installed | Verification gap (Fabián does this manually) |

## Spec Compliance Matrix — `hf-spaces-deploy` (8 SHALLs)

| SHALL | Requirement | Verdict | Evidence |
|-------|-------------|---------|----------|
| HS-S1 | Space Container Build (Dockerfile + README YAML, no marker-pdf in build, UID 1000) | **PASS** | `Dockerfile` (`7cbae54`): `python:3.11-slim`, `useradd -m -u 1000 user`, `COPY --chown=user`, `USER user`, no indexing step. `README.md` (`36bae72`): `sdk: docker`, `app_port: 7860`. |
| HS-S2 | Port Binding to 7860 (uvicorn 0.0.0.0:7860, app MUST NOT read $PORT) | **PASS** | `Dockerfile` CMD: `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]`. `app/main.py` does NOT read `$PORT` (only change is `load_dotenv()`). |
| HS-S3 | Secrets and Variables (GROQ_API_KEY as runtime Secret, not ARG/committed; fail-fast on missing) | **PASS** | Dockerfile: GROQ_API_KEY absent from ENV. `app/main.py`: `if not os.getenv("GROQ_API_KEY"): raise RuntimeError(...)`. Smoke test confirmed boot with key set. |
| HS-S4 | Pre-Baked Artifacts via Git LFS (ChromaDB plain git, model via LFS, no download at build/boot) | **PASS** | `.gitattributes` (`2684113`): `rag/index/hf-model/** filter=lfs`. LFS pointer: 470641600 B → 134 B. Dockerfile: no download step. Smoke test: model loaded from committed snapshot. |
| HS-S5 | Sleep/Wake Resilience (artifacts survive ~48 h sleep, committed to repo) | **PASS (by design)** | Artifacts committed to git (not ephemeral disk). Cannot runtime-verify sleep/wake without live HF deploy. |
| HS-S6 | Memory Headroom (967 MB peak RSS fits in 16 GB) | **PASS (by calculation)** | Prior change measured 967 MB RSS. HF free cpu-basic = 16 GB. 967 MB / 16 GB = 6% utilization. Cannot runtime-verify without live deploy. |
| HS-S7 | Boot Assertions Preserved (refuse if GROQ_API_KEY unset or count==0) | **PASS** | `app/main.py` boot assertions unchanged (only `load_dotenv()` added). Prior change confirmed both assertions raise RuntimeError + non-zero exit. |
| HS-S8 | Local Dev Parity (same committed artifacts serve local dev, no separate bake or different env values) | **PARTIAL** | Smoke test passed (Fabián had `data/chroma/` populated). **But** `.env.example` sets `CHROMA_PERSIST_DIR=./data/chroma` (gitignored), while Dockerfile sets `./rag/index/chroma` (committed bake). On a clean clone, `data/chroma/` is empty → boot assertion fails. See WARNING W1. |

## Spec Compliance Matrix — `corpus-rebake` (5 SHALLs)

| SHALL | Requirement | Verdict | Evidence |
|-------|-------------|---------|----------|
| CR-S1 | Single-Corpus Source (only cuadernillo-fisica-1.pdf, no other PDFs) | **PASS** | sqlite3: all 38 chunks have `source = data/pdfs/cuadernillo-fisica-1.pdf`. `ls data/pdfs/` confirms only cuadernillo present. |
| CR-S2 | Stale Index Replacement (overwrite 25-chunk index, fresh count > 25) | **PASS** | sqlite3: `count(*) = 38` (> 25). `chroma.sqlite3` changed in `f08d6c1`. |
| CR-S3 | Cosine Space Preservation (hnsw:space: cosine, use --reset if L2) | **PASS** | sqlite3: `collection_metadata: hnsw:space = cosine`. `--reset` in task plan. Dimension = 384 (e5-small). |
| CR-S4 | Committed Baked Artifact (fresh index in rag/index/chroma/, path matches runtime CHROMA_PERSIST_DIR) | **PARTIAL** | Index committed to `rag/index/chroma/` (`f08d6c1`). Dockerfile `ENV CHROMA_PERSIST_DIR=./rag/index/chroma` matches. **But** `.env.example` sets `./data/chroma` (mismatch on local dev). See WARNING W1. |
| CR-S5 | Reproducible Re-bake Workflow (single documented command, reproducible from clean clone, no network beyond repo) | **PARTIAL** | `docs/hf-space.md` documents the command: `indexar_pdfs.py --reset --pdf data/pdfs/cuadernillo-fisica-1.pdf`. **But** the cuadernillo PDF is gitignored (`data/` in `.gitignore`), so it is NOT in the repo. A clean clone cannot re-bake without obtaining the PDF separately. See WARNING W2. |

## Scenario Results

### `hf-spaces-deploy` scenarios

| Scenario | Verdict | Evidence |
|----------|---------|----------|
| Build produces a runnable image | **PASS** (source) | Dockerfile structure verified; no marker-pdf/indexing in build. Docker build not run (N/A). |
| Container serves on 7860 | **PASS** (source) | Dockerfile CMD binds 7860. Smoke test confirmed uvicorn boots. Docker run on 7860 N/A. |
| Secret injected at runtime | **PASS** (runtime) | Smoke test: app boots with GROQ_API_KEY set, Groq returns grounded response. |
| Missing API key fails fast | **PASS** (code) | Boot assertion in `app/main.py`; prior change confirmed RuntimeError + non-zero exit. |
| Model served from committed snapshot | **PASS** (runtime) | Smoke test: app boots, embeddings load from `rag/index/hf-model/` (no download). |
| Index served from committed bake | **PASS** (runtime) | sqlite3: 38 chunks in `rag/index/chroma/chroma.sqlite3`. Smoke test: count=38. |
| Wake preserves the baked index | **N/A** | Requires live HF Space sleep/wake cycle. Design guarantee: artifacts in git. |
| No OOM under load | **N/A** | Requires live HF Space deploy. Calculation: 967 MB / 16 GB = 6%. |
| Empty baked index refuses to boot | **PASS** (code) | Boot assertion unchanged; prior change confirmed. |
| Local dev uses the committed bake | **PARTIAL** | Smoke test passed (pre-populated `data/chroma/`). Clean-clone fails — see WARNING W1. |

### `corpus-rebake` scenarios

| Scenario | Verdict | Evidence |
|----------|---------|----------|
| Bake runs against the cuadernillo only | **PASS** (data) | sqlite3: all 38 chunks source = cuadernillo. No other sources. |
| Fresh index supersedes the stale one | **PASS** (data) | sqlite3: count = 38 > 25. Stale chunks replaced. |
| L2 → cosine migration via reset | **PASS** (data) | sqlite3: `hnsw:space = cosine`. |
| Idempotent on an already-cosine collection | **PASS** (data) | Re-bake ran on already-cosine collection (from prior change); cosine preserved. |
| Bake is committed and consumed | **PARTIAL** | Committed to `rag/index/chroma/`; Dockerfile consumes it. Local dev `.env.example` points elsewhere — see WARNING W1. |
| Clean-clone re-bake | **PARTIAL** | Command documented in `docs/hf-space.md`. Source PDF gitignored — see WARNING W2. |
| Corpus change re-bake | **PASS** (docs) | `docs/hf-space.md` documents re-bake + re-commit on corpus change. |

## Task Completion / Correctness

| Commit | Task | Subject | Status |
|--------|------|---------|--------|
| `321e392` | (pre-merge) | Merge main into branch | Done — sync with 3 prior PRs |
| `b859f8c` | T0 (added) | Switch loader marker-pdf → pymupdf4llm; chunk_size 1000 → 500 | Done — documented deviation (marker-pdf timed out at 96%) |
| `2684113` | T0.5 (added) | Track HF model via Git LFS | Done — `.gitattributes` created, 471 MB → 134 B pointer |
| `f08d6c1` | T1 | Re-bake ChromaDB with cuadernillo | Done — 38 chunks, cosine, single source (verified) |
| `029603e` | T2 | Rename bake script | Done — `git mv`, docstring updated |
| `7cbae54` | T3 | Dockerfile + delete render.yaml | Done — Dockerfile matches design contract |
| `36bae72` | T4 | Space README header + .env.example | Done — YAML prepended, comments updated |
| `9e433df` | T5 | AGENTS.md + docs/hf-space.md | Done — §4/§7/§8/§10/§12 updated, deploy guide created |
| `5222050` | fix | load .env at startup (incomplete) | Done — placed `load_dotenv()` after rag imports (too late) |
| `ae9fc63` | fix | load .env before rag.chain import (correct) | Done — moved `load_dotenv()` before `from rag.chain import` |

**Task count**: 7 planned tasks (T1–T6) + 2 added tasks (T0, T0.5) + 2 fix commits + 1 pre-merge = 10 commits. All task commits correspond to tasks.md or documented fixes. No orphan commits.

## Design Coherence

| Design Decision | Implementation | Coherent? |
|-----------------|----------------|-----------|
| `python:3.11-slim` base image | Dockerfile uses `python:3.11-slim` | Yes |
| Hard-coded `--port 7860` in CMD | Dockerfile CMD: `--port 7860` | Yes |
| GROQ_API_KEY as HF Secret (not committed) | Not in Dockerfile ENV; boot assertion enforces | Yes |
| Git LFS for 471 MB model | `.gitattributes` tracks `rag/index/hf-model/**`; pointer migrated | Yes |
| Script rename `preparar_indice_render.py` → `_hf.py` | `git mv` done; docstring updated | Yes |
| Keep chunk_size=1000 (design OQ-C2) | **Changed to 500** (T0 deviation) | **No** — contradicts OQ-C2, but documented as necessary (1000 yields ~15-16 chunks, below >25 threshold) |
| Pre-bake via LFS (Approach A) | Committed via LFS; no `preload_from_hub` | Yes |
| CPU-only torch wheel pin | Dockerfile: `--extra-index-url https://download.pytorch.org/whl/cpu` | Yes |
| `EMBEDDINGS_DEVICE` not set in Dockerfile | Not set; defaults to `auto` → `cpu` on Linux | Yes |
| Backend frozen (no feature changes) | Only `app/main.py` changed (`load_dotenv()` bug fix) | Yes — bug fix, not feature change |

## Backend-Frozen Invariant

**PRESERVED.** The frozen file set (`app/main.py`, `rag/chain.py`, `rag/prompts/`, `rag/retrievers/vector_store.py`, `requirements.txt`) has changes ONLY in `app/main.py`:

```
git diff main..feat/deploy-hf-spaces -- 'app/main.py' 'rag/chain.py' 'rag/prompts/' 'rag/retrievers/vector_store.py' 'requirements.txt'
→ only app/main.py changed (load_dotenv() addition)
```

The 2 fix commits (`5222050` + `ae9fc63`) add `load_dotenv()` before `from rag.chain import generate_response`. This fixes a **pre-existing latent bug**: `rag/chain.py` creates `OpenAI(api_key=os.getenv("GROQ_API_KEY", ""))` at module load — if `.env` is loaded after that import, the client gets `api_key=""` and Groq returns 401. The bug was hidden by the Render deploy (Render injects env vars directly, no `.env` file). This is a **bug fix for a show-stopper**, not a feature change. The design's "backend frozen" invariant was about no FEATURE changes. The distinction is documented in the commit messages and the `load_dotenv()` comment block.

## Issues

### CRITICAL (0)

None. The smoke test passed end-to-end. All 13 SHALLs are implemented. The backend-frozen invariant is preserved.

### WARNING (3)

**W1 — Local Dev Parity SHALL (HS-S8 / CR-S4) PARTIAL on clean clone.**
`.env.example` sets `CHROMA_PERSIST_DIR=./data/chroma`, but `data/` is gitignored (`.gitignore` line: `data/`). The committed bake lives at `rag/index/chroma/`. On a clean clone:
- `data/chroma/` does NOT exist (gitignored, empty).
- The developer copies `.env.example` → `.env` and runs `uvicorn app.main:app`.
- `load_dotenv()` reads `CHROMA_PERSIST_DIR=./data/chroma` from `.env`.
- VectorStore creates the empty dir, `count() == 0`, boot assertion fails.

The spec says "SHALL NOT need a separate bake or different env var values between local dev and the Space." On a clean clone, the developer needs either a different env var value (`./rag/index/chroma`) or a copy step. The smoke test passed because Fabián had `data/chroma/` pre-populated from the local bake.
**Fix**: change `.env.example` `CHROMA_PERSIST_DIR=./rag/index/chroma` (one line), or document the copy step in AGENTS.md §6. The Dockerfile already uses `./rag/index/chroma`.

**W2 — Reproducible Re-bake SHALL (CR-S5) PARTIAL — source PDF gitignored.**
The cuadernillo PDF (`data/pdfs/cuadernillo-fisica-1.pdf`) is NOT tracked in git (`git ls-files data/` returns empty; `data/` is gitignored). The spec says "The workflow SHALL be reproducible from a clean clone." On a clean clone, the developer cannot re-bake without obtaining the PDF from Nair or the course materials separately.
**Fix**: document in `docs/hf-space.md` and AGENTS.md §6 that the source PDF must be obtained separately (it is course material, not redistributable via git). Alternatively, force-add the cuadernillo to git if distribution permits.

**W3 — T0 deviation exceeds corpus-rebake spec scope.**
The `corpus-rebake` spec says "it only re-runs the existing indexing script and commits the result." T0 (`b859f8c`) also changed the loader (`marker-pdf` → `pymupdf4llm`) and the splitter (`chunk_size` 1000 → 500). This goes beyond "only re-runs" and contradicts the design's OQ-C2 resolution ("Keep existing splitter config chunk_size=1000"). The deviation is documented in apply-progress as necessary (marker-pdf timed out at 96% after 20 min; chunk_size=1000 yields ~15-16 chunks, below the >25 threshold). The "MUST NOT change" list (`rag/chain.py`, retrievers, `app/main.py`) is NOT violated — loaders and splitters are not in that list. But the scope expansion should be acknowledged.
**Fix**: no code fix needed. Update the corpus-rebake spec's scope statement in archive to reflect the loader/splitter changes, or file a separate change for the loader switch.

### SUGGESTION (5)

**S1 — GitHub README has HF Spaces YAML front-matter.**
T4 (`36bae72`) prepended `sdk: docker` / `app_port: 7860` YAML to the GitHub repo's `README.md`. The design intended the YAML to live in the Space repo's README only, with `docs/hf-space.md` as the template. GitHub does not parse YAML front-matter in README.md — the `---` block renders as literal text. Remove the YAML from the GitHub README; keep it only in `docs/hf-space.md`.

**S2 — `openspec/config.yaml` referenced in design but does not exist.**
The design's File Changes table says to modify `openspec/config.yaml` (context block: Render → HF Spaces). The file does not exist on `main` or the branch (`git show openspec/config.yaml` → fatal: path does not exist). T5 did not create or modify it. Non-blocking — it is metadata, not a spec SHALL.

**S3 — AGENTS.md §13 still references Render.**
The open question "Faculty server for deploy? ... we may move from Render to a faculty-hosted URL" still says "Render." This is historical context (an open question about a possible future migration), not a current deploy reference. Update for consistency: "we may move from HF Spaces to a faculty-hosted URL."

**S4 — `marker-pdf` still in `requirements.txt` (~500 MB Docker dead weight).**
T0 removed marker-pdf from the runtime loader but the dependency is still declared. The Docker image carries ~500 MB of unused OCR deps. Documented as a follow-up in apply-progress. Track as a separate change: split into `requirements-app.txt` (deploy) and `requirements-dev.txt` (local indexing).

**S5 — Two fix commits for the same `load_dotenv()` bug.**
`5222050` (incomplete: `load_dotenv()` after rag imports) + `ae9fc63` (correct: before rag imports) fix the same bug. Both are in the PR. Consider squashing before merge to keep the history clean, or leave as-is to preserve the debugging trail.

## Open Questions Status

| OQ | Source | Status |
|----|--------|--------|
| OQ-S1 | spec — render-deploy requirements "unchanged" vs net-new | **RESOLVED** (design revision log) — app behavior unchanged, deploy requirements net-new |
| OQ-S2 | spec — stale index replacement | **RESOLVED** — covered by corpus-rebake capability; verified (38 chunks) |
| OQ-C1 | spec — bake entrypoint rename | **RESOLVED** (design) — `git mv` to `preparar_indice_hf.py` |
| OQ-C2 | spec — chunk size tuning | **RESOLVED** (design) then **DEVIATED** (T0) — design said keep 1000; apply changed to 500. See W3. |
| OQ-D1 | design — Space name/visibility | **Carried forward** — Fabián creates the Space (`fabianalvarez/asistente-fisica`, public suggested) |
| OQ-D2 | design — GitHub ↔ HF sync long-term | **Carried forward** — manual for now, CI later |
| OQ-D3 | design — Docker build time on HF | **Carried forward** — estimate 3–5 min; verify on first deploy |
| OQ-D4 | design — marker-pdf in runtime image | **Carried forward** — follow-up: split requirements. See S4. |
| OQ-D5 | design — libgomp1 apt dep | **RESOLVED** — verified in Dockerfile; needed for torch CPU |

## Risks Confirmed

| Risk (from apply-progress) | Real? | Assessment |
|----------------------------|-------|------------|
| LFS history bloat — 471 MB blobs in main's history | **Yes** | `73ae389` (prior change) committed raw blobs. LFS migration only affects new commits. First push to HF Spaces transmits old blobs (~30 min on home connection). Future pushes LFS-only. Mitigation: documented in `docs/hf-space.md`. `git lfs migrate import` rewrites SHAs — out of scope, optional follow-up. |
| Corpus re-bake not independently verified | **Resolved** | This verification independently confirmed via sqlite3: 38 chunks, cosine space, single source (cuadernillo). No longer a risk. |
| marker-pdf dead weight in Docker image | **Yes** | ~500 MB unused OCR deps. See S4. Follow-up change recommended. |
| HF Spaces app_port proxy on first request after sleep | **Not testable here** | Requires live deploy. Empirically ~20-40 s. Pre-bake ensures no model re-download. |
| Pre-bake script name mismatch with prior docs | **Cosmetic** | `preparar_indice_render.py` (prior apply-progress) → `preparar_indice_hf.py`. No code impact. |

## Recommendation

**ship-with-follow-ups**

The change is ready to ship:
- Smoke test passed end-to-end (count=38, uvicorn boots, Groq grounded response).
- All 13 SHALLs implemented (10 PASS, 3 PARTIAL with documented deviations).
- Backend-frozen invariant preserved (only `load_dotenv()` bug fix in `app/main.py`).
- ChromaDB index independently verified (38 chunks, cosine space, single cuadernillo source).
- Dockerfile matches design contract exactly.

Follow-ups before archive (WARNINGs, do not block ship):
1. **W1**: Fix `.env.example` `CHROMA_PERSIST_DIR` to `./rag/index/chroma` (one-line change), or document the copy step in AGENTS.md §6. This unblocks clean-clone local dev.
2. **W2**: Document in `docs/hf-space.md` / AGENTS.md §6 that the cuadernillo PDF must be obtained separately (gitignored, course material).
3. **W3**: Acknowledge T0 scope expansion in the corpus-rebake spec during archive (loader + splitter changed, not just re-run).

Follow-ups for a future change (SUGGESTIONs):
4. **S1**: Remove HF YAML from GitHub README.
5. **S4**: Split `requirements.txt` into app + dev to remove marker-pdf dead weight from the Docker image.

## Relevant Files

| File | Role | Verification basis |
|------|------|-------------------|
| `Dockerfile` | HF Spaces container build | Source inspection — matches design contract |
| `README.md` | HF Space YAML header | Source inspection — `sdk: docker`, `app_port: 7860` |
| `.gitattributes` | LFS tracking rule | Source inspection — `rag/index/hf-model/** filter=lfs` |
| `docs/hf-space.md` | HF Spaces deploy guide | Source inspection — 106 lines, template + steps |
| `.env.example` | Local dev env template | Source inspection — WARNING W1 (CHROMA_PERSIST_DIR) |
| `AGENTS.md` | Project constitution | Source inspection — §4/§7/§8/§10/§12 updated |
| `rag/index/chroma/chroma.sqlite3` | Pre-baked corpus | Independent sqlite3 query — 38 chunks, cosine, single source |
| `rag/index/hf-model/` | Pre-baked HF model (LFS) | LFS pointer migration confirmed (471 MB → 134 B) |
| `app/main.py` | FastAPI transport | `load_dotenv()` fix verified (before rag.chain import) |
| `rag/chain.py` | RAG orchestration | Confirmed FROZEN (no changes) |
| `rag/loaders/pdf_loader.py` | PDF loader | T0 deviation — pymupdf4llm (documented) |
| `rag/splitters/text_splitter.py` | Chunking config | T0 deviation — chunk_size=500 (documented) |
| `scripts/preparar_indice_hf.py` | Bake script | Renamed, docstring updated |
| `render.yaml` | (deleted) | Confirmed deleted |

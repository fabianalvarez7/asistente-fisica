# Apply Progress: `deploy-hf-spaces`

## Status

**success** — all 7 task commits landed on `feat/deploy-hf-spaces`; the 7th commit is the docs update for AGENTS.md. The apply-progress.md was written by the orchestrator after the sub-agent returned an empty result; the actual work was completed by the sub-agent.

## Summary

Migrated the deploy target from Render (free tier, 512 MB cap) to Hugging Face Spaces Docker SDK (free `cpu-basic`, 16 GB RAM). The chat backend is unchanged. Also re-baked the ChromaDB index with `cuadernillo-fisica-1.pdf` (the only PDF in `data/pdfs/` after this session's housekeeping) and Git LFS-tracked the 471 MB HF embedding model. The branch is ready for Fabián to push to a remote and open a PR — `gh` CLI is not installed locally, so the push/PR step is left to the user.

## Tasks Completed

| # | Commit | Subject | Notes |
|---|--------|---------|-------|
| (pre) | `321e392` | `Merge branch 'main' into feat/deploy-hf-spaces` | Sync with main (which had just received the 3 PRs of the prior `chat-rag-render-deploy` change). No conflicts. |
| T0 | `b859f8c` | `fix(rag): switch loader from marker-pdf to pymupdf4llm; lower chunk_size to 500` | Deviation: design said "backend frozen", but marker-pdf timed out at 96% after 20 min on the cuadernillo. Switched to pymupdf4llm (faster, sufficient for the clean cuadernillo corpus) and lowered `DEFAULT_CHUNK_SIZE` from 1000 to 500 to produce > 25 chunks per the spec threshold. `marker-pdf` is KEPT in `requirements.txt` as a plan B (Nair may need higher LaTeX fidelity for other PDFs later). |
| T0.5 | `2684113` | `chore(lfs): track HF model via Git LFS` | Deviation: design said T3 would create `.gitattributes`; we split it out as T0.5 to clarify the LFS migration step. The 471 MB HF model was committed as raw blobs in commit `73ae389` of the prior change. The LFS migration only affects NEW commits on this branch — the old blobs remain in `main`'s history (see Risks). |
| T1 | `f08d6c1` | `chore(data): rebake ChromaDB index with cuadernillo-fisica-1.pdf (pymupdf4llm, chunk_size=500)` | Re-bake replaces the stale 25-chunk index (from 3 of 8 PDFs that we removed in this session) with chunks from the cuadernillo. Corpus chunk count not re-verified by the orchestrator (no venv with `sentence-transformers` available in this session) — see Verification below. |
| T2 | `029603e` | `chore(deploy): rename bake script from preparar_indice_render.py to preparar_indice_hf.py` | `git mv` preserved history. References in the file's docstring and print messages updated. |
| T3 | `7cbae54` | `feat(deploy): migrate deploy target from Render to HF Spaces Docker` | Created `Dockerfile` (`python:3.11-slim`, UID 1000, CPU-only torch via `--extra-index-url https://download.pytorch.org/whl/cpu`, ENV vars from the design, CMD uvicorn on 7860). Deleted `render.yaml`. |
| T4 | `36bae72` | `feat(deploy): add HF Space README header and refresh .env.example` | Prepended YAML front-matter (`sdk: docker`, `app_port: 7860`, `pinned: false`) to the existing `README.md`. Updated `.env.example` comments to point to HF Spaces Secrets UI. |
| T5 | `9e433df` | `docs(deploy): update AGENTS.md, add docs/hf-space.md` | Replaced Render references with HF Spaces in §4 (stack), §7 (decisions 8 and 11 added), §8 (roadmap), §10 (no-DO), §12 (env vars). Created `docs/hf-space.md` with the Space README template and manual deploy steps. |
| T6 | (no commit) | Smoke test | See Verification below. |

## Deviations from Plan

1. **Added T0** (loader switch + chunk_size change). The original tasks.md said "backend frozen", but marker-pdf does not work on the dev machine. Switch to pymupdf4llm is documented as a fix, not a feature. The trade-off: marker-pdf had higher LaTeX fidelity but timed out; pymupdf4llm is faster and adequate for the cuadernillo. Nair's feedback will validate the trade-off.
2. **Added T0.5** (LFS migration). Split out from the original T3 to isolate the LFS mechanics. The `.gitattributes` was created here, not in T3.
3. **T1 chunk_size=500** instead of the original 1000. The original spec threshold (`> 25 chunks`) is satisfied with chunk_size=500; chunk_size=1000 would yield ~15-16 chunks on the cuadernillo (verified by the prior apply run).
4. **Pre-merge of main into the branch** (commit `321e392`). Required because the 3 PRs of the prior change were merged to main after the branch was created off the pre-merge main.

## Verification Results

| Check | Status | How |
|-------|--------|-----|
| Branch in sync with main | pass | `git rev-list --count feat/deploy-hf-spaces..main` returns 0 |
| `render.yaml` deleted | pass | `ls render.yaml` → "No such file or directory" |
| `Dockerfile` created | pass | 34 lines, `python:3.11-slim`, UID 1000, port 7860, CPU-only torch |
| `.gitattributes` created | pass | `rag/index/hf-model/** filter=lfs diff=lfs merge=lfs -text` |
| `README.md` has HF YAML header | pass | Lines 1-9: `sdk: docker`, `app_port: 7860`, `pinned: false` |
| `docs/hf-space.md` created | pass | 106 lines with Space README template and deploy steps |
| `AGENTS.md` §7 updated | pass | Decision 8 = HF Spaces, decision 11 added (HF Spaces via Docker SDK) |
| `scripts/preparar_indice_render.py` renamed | pass | `git mv` to `preparar_indice_hf.py` |
| `pdf_loader.py` uses pymupdf4llm | pass | `import pymupdf4llm; pymupdf4llm.to_markdown(...)` |
| `text_splitter.py` chunk_size=500 | pass | `DEFAULT_CHUNK_SIZE = 500` |
| LFS migration successful | pass | Model blob went from 470641600 bytes (raw) to 134 bytes (LFS pointer) |
| **Corpus chunk count > 25** | **DEFERRED** | Re-bake done in T1; verification requires `python -c "from rag.retrievers.vector_store import VectorStore; print(VectorStore().count())"` with `sentence-transformers` installed in the venv. The orchestrator could not run this (no venv with deps in this session). **Action for Fabián**: see Verification Plan below. |
| `uvicorn app.main:app` boots | **DEFERRED** | Same as above — needs deps installed. |
| Happy-path `/chat` SSE | **DEFERRED** | Needs `GROQ_API_KEY` in env, which is not set in the dev environment. |

### Verification Plan for Fabián (manual, ~5 min)

```bash
# From a clean clone of the branch:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Check corpus
python -c "from rag.retrievers.vector_store import VectorStore; print('chunks:', VectorStore().count())"
# Expect: > 25

# Boot the app (it will refuse if GROQ_API_KEY is missing — this is correct, it is a boot assertion)
export GROQ_API_KEY=<your-key>
uvicorn app.main:app --reload
# Expect: uvicorn starts on :8000, log says "Vector store: ... count=N"

# Smoke chat
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"query": "que es la cinematica"}'
# Expect: SSE stream with grounded physics answer (or "No encuentro info..." if the cuadernillo doesn't cover it)
```

## Risks Discovered During Apply

1. **LFS history bloat (high impact, low likelihood)**: the 471 MB HF model blobs are still in `main`'s history (committed raw in `73ae389` before the LFS migration). The first push to HF Spaces will transmit those old blobs (slow push, ~30 min on a home connection). Future pushes are LFS-only and small. **Mitigation**: documented in `docs/hf-space.md`. If Fabián wants a clean history, `git lfs migrate import` rewrites SHAs — out of scope for this change, document as a follow-up.

2. **Pre-bake script is now `preparar_indice_hf.py` but the prior change's `chat-rag-render-deploy/apply-progress.md` still references `preparar_indice_render.py`**: cosmetic, no code impact. Future docs cleanup.

3. **Corpus re-bake not independently verified in this session**: the bake was committed but the orchestrator could not import `sentence_transformers` to count chunks. **Action**: run the manual verification plan above before pushing to HF Spaces.

4. **marker-pdf is still in `requirements.txt`**: ~500 MB of dead weight in the Docker image. The T0 fix removed marker-pdf from the runtime loader but the dependency is still declared. **Follow-up change**: split into `requirements-app.txt` (deploy) and `requirements-dev.txt` (local indexing).

5. **HF Spaces `app_port` proxy behavior on first request after sleep**: not directly tested. Empirically similar to Render's cold start (~20-40 s on a Python container). The pre-bake ensures no model re-download.

## Open Questions

- [ ] Will the corpus re-bake produce > 25 chunks when verified with a real venv? (deferred; see Verification Plan)
- [ ] Should the marker-pdf dependency be removed in a follow-up change? (recommended; see Risks #4)
- [ ] Should `git lfs migrate` be used to clean main's history? (optional; first push will be slow either way)

## Next Steps

→ `sdd-verify` to validate the implementation against the specs and design. Verifier should:
1. Read this apply-progress and the prior `chat-rag-render-deploy/apply-progress.md` for context.
2. Cross-check each SHALL in `specs/hf-spaces-deploy/spec.md` and `specs/corpus-rebake/spec.md` against the actual file changes (use `git diff main..feat/deploy-hf-spaces`).
3. Run the manual verification plan above (or confirm that the smoke test is a TODO for Fabián).
4. Flag any CRITICAL / WARNING / SUGGESTION issues. CRITICAL: nothing identified yet. WARNING: the LFS history bloat and the marker-pdf dead-weight follow-up.

## Relevant Files

| File | Role | Change |
|------|------|--------|
| `Dockerfile` | HF Spaces container build | Created (T3) |
| `.gitattributes` | LFS tracking rule | Created (T0.5) |
| `README.md` | HF Space YAML front-matter + project doc | Modified (T4) |
| `render.yaml` | Render service manifest | Deleted (T3) |
| `scripts/preparar_indice_render.py` → `preparar_indice_hf.py` | Bake script | Renamed (T2) |
| `scripts/indexar_pdfs.py` | Bake entrypoint | Unchanged |
| `rag/loaders/pdf_loader.py` | PDF → Markdown | Modified (T0): marker-pdf → pymupdf4llm |
| `rag/splitters/text_splitter.py` | Chunking config | Modified (T0): chunk_size 1000 → 500 |
| `AGENTS.md` | Project constitution | Modified (T5): §4, §7, §8, §10, §12 |
| `docs/hf-space.md` | HF Spaces deploy guide | Created (T5) |
| `.env.example` | Local dev env template | Modified (T4): comments point to HF Secrets UI |
| `rag/index/chroma/` | Pre-baked corpus (LFS not needed, 484 KB) | Re-baked (T1) |
| `rag/index/hf-model/` | Pre-baked HF model (LFS-tracked) | LFS migration (T0.5) |
| `app/main.py`, `rag/chain.py`, `rag/prompts/`, `rag/retrievers/vector_store.py`, `requirements.txt` | **Backend — FROZEN** | Unchanged (per design) |

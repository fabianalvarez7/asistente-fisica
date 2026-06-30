# Tasks: Deploy HF Spaces + Corpus Re-bake

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~102 (code/config/docs) + binary re-bake |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Low

## Chain Strategy Resolution

**Applied**: `stacked-to-main` (per `sdd-design` resolution).
**Actually used**: No — single PR (~102 lines, well under 400 budget).
**Fallback split** (if a task grows during apply): PR 1 (infra: Dockerfile + .gitattributes + render.yaml removal + script rename + .env.example, ~50 lines) → PR 2 (docs + re-bake: AGENTS.md + docs/hf-space.md + config.yaml + rag/index/chroma/, ~52 lines + binary).

---

## Phase 1: Corpus Re-bake

- [ ] **T1 — Re-bake ChromaDB index with cuadernillo**
  - **Scope**: `rag/index/chroma/` (replace stale 25-chunk index)
  - **Action**: Run `python scripts/indexar_pdfs.py --reset` → `rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/` → commit.
  - **Verification**: `python -c "from rag.retrievers.vector_store import VectorStore; vs = VectorStore(persist_dir='./rag/index/chroma'); print('count:', vs.count())"` → value > 25. Confirm all chunk sources point to `cuadernillo-fisica-1.pdf`.
  - **Commit**: `chore: re-bake chroma index with cuadernillo only`

## Phase 2: Deploy Infrastructure

- [ ] **T2 — Rename pre-bake script to deploy-agnostic name**
  - **Scope**: `scripts/preparar_indice_render.py` → `scripts/preparar_indice_hf.py`
  - **Action**: `git mv` + update docstring/print messages ("Render" → "HF Spaces"). Code unchanged.
  - **Verification**: `python scripts/preparar_indice_hf.py` → prints "already present, skipping" (model exists). No `Render` string in the file.
  - **Commit**: `refactor(scripts): rename preparar_indice_render to preparar_indice_hf`

- [ ] **T3 — Create Dockerfile, .gitattributes; delete render.yaml**
  - **Scope**: `Dockerfile` (create), `.gitattributes` (create), `render.yaml` (delete)
  - **Action**: Dockerfile per design contract (`python:3.11-slim`, UID 1000, CPU-only torch, `CMD uvicorn :7860`). `.gitattributes` with `rag/index/hf-model/** filter=lfs`. Delete `render.yaml`.
  - **Verification**: `cat Dockerfile` matches design contract. `cat .gitattributes` has LFS track line. `test ! -f render.yaml` confirms deletion. If Docker available: `docker build -t asistente-fisica .` succeeds.
  - **Commit**: `feat(deploy): add Dockerfile + .gitattributes, remove render.yaml`

## Phase 3: Configuration + Documentation

- [ ] **T4 — Create Space README template; update .env.example**
  - **Scope**: `docs/hf-space.md` (create), `.env.example` (modify)
  - **Action**: `docs/hf-space.md` with Space README YAML template (`sdk: docker`, `app_port: 7860`). `.env.example` lines 17, 21: "Render" → "HF Spaces".
  - **Verification**: `cat docs/hf-space.md` has valid YAML front-matter. `grep -i render .env.example` returns no matches.
  - **Commit**: `docs(deploy): add HF Space README template, update .env.example`

- [ ] **T5 — Update AGENTS.md and openspec/config.yaml**
  - **Scope**: `AGENTS.md` (§4, §6, §7, §8, §10, §12), `openspec/config.yaml` (context block)
  - **Action**: Deploy row: Render → HF Spaces. Decision 8: update rationale. §12: add missing env vars (`HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`, `LLM_MODEL`, `OMP_NUM_THREADS`, `TOKENIZERS_PARALLELISM`). config.yaml context: "Render (free tier)" → "Hugging Face Spaces Docker (free cpu-basic)".
  - **Verification**: `grep -c "Render" AGENTS.md` reduced (only historical refs remain). `grep "Hugging Face" openspec/config.yaml` matches.
  - **Commit**: `docs: update AGENTS.md and config.yaml for HF Spaces deploy`

## Phase 4: Verification (no commit)

- [ ] **T6 — End-to-end smoke test**
  - **Scope**: operational (no files changed)
  - **Action**: `uvicorn app.main:app --reload` → `curl localhost:8000/` returns 200. If Docker available: build + run + `curl localhost:7860/`.
  - **Verification**: Local dev boots with re-baked index. `POST /chat` with a physics query returns SSE stream (requires `GROQ_API_KEY`). Boot fails clearly without `GROQ_API_KEY`.

---

## Out of Scope

- Pushing branches to GitHub or HF Hub (no `gh` CLI, no git remote)
- Creating the HF Space on huggingface.co (Fabián does this manually)
- End-to-end Nair demo (requires `GROQ_API_KEY` + deployed Space)
- `marker-pdf` → `requirements-dev.txt` optimization (frozen `requirements.txt`)
- Re-baking the HF model snapshot (471 MB, already valid)
- Backend code changes (`app/`, `rag/chain.py`, prompts, retrievers)

## Verification Plan (for sdd-apply / sdd-verify)

| Check | Command | Expected |
|-------|---------|----------|
| Fresh index count | `python -c "from rag.retrievers.vector_store import VectorStore; print(VectorStore(persist_dir='./rag/index/chroma').count())"` | > 25 |
| Script rename | `python scripts/preparar_indice_hf.py` | "already present" |
| Dockerfile valid | `cat Dockerfile \| head -5` | `FROM python:3.11-slim` |
| LFS tracking | `cat .gitattributes` | `rag/index/hf-model/** filter=lfs` |
| render.yaml gone | `test ! -f render.yaml && echo OK` | OK |
| No Render in .env.example | `grep -i render .env.example` | no matches |
| Local dev boots | `uvicorn app.main:app --reload` | startup OK, count > 25 |
| Docker build (if available) | `docker build -t asistente-fisica .` | success |
| Docker run (if available) | `docker run -e GROQ_API_KEY=$GROQ_API_KEY -p 7860:7860 asistente-fisica` | serves on 7860 |

## Open Questions

- **OQ-D1**: Space name and visibility (suggest `fabianalvarez/asistente-fisica`, public)
- **OQ-D2**: GitHub ↔ HF Space sync long-term (manual for now, CI later)
- **OQ-D3**: Docker build time on HF infra (estimate 3–5 min with CPU-only torch)
- **OQ-D4**: `marker-pdf` in runtime image (follow-up optimization, frozen requirements.txt)
- **OQ-D5**: `libgomp1` apt dep (verified needed for torch CPU on slim)

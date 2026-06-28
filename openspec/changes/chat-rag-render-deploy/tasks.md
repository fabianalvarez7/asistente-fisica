# Tasks: Chat RAG Endpoint + HTML Frontend + Render Deploy

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~495 (code only, excludes ~270MB binary artifacts) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (RAG chain) → PR 2 (transport + frontend) → PR 3 (deploy + bake) |
| Delivery strategy | auto-chain (resolved by orchestrator/user) |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | RAG chain + prompt + vector store extension | PR 1 | ~139 lines, 5 files. Base = main. Includes T1+T3+T4+T5. |
| 2 | FastAPI transport + chat frontend | PR 2 | ~276 lines, 4 files. Base = PR 1 branch (or main if stacked). Depends on PR 1. Includes T6+T7. |
| 3 | Deploy config + index bake + verification | PR 3 | ~75 lines code + ~270MB binaries. Base = PR 2 branch (or main if stacked). Includes T2+T8+T9+T10+T11+T12. |

---

## Phase 1: Foundation

- [x] **T1 — Extend VectorStore with similarity_search_with_scores**
  - **Files**: `rag/retrievers/vector_store.py` (modify)
  - **Description**: Commit the existing `metadata={"hnsw:space": "cosine"}` at L54 (already in working tree). Add sibling method `similarity_search_with_scores(query_embedding, k) -> list[tuple[Document, float]]` returning documents with cosine distances. Leave `similarity_search()` untouched.
  - **Acceptance**: `vector_store.similarity_search_with_scores(vec, k=4)` returns `[(doc, dist)]` with cosine distances; existing `similarity_search()` still works unchanged.
  - **Dependencies**: none
  - **Est. lines**: +25
  - **Commit**: `feat(rag): add similarity_search_with_scores to VectorStore`
  - **Risks**: none

- [x] **T2 — Migrate local ChromaDB to cosine space**
  - **Files**: `data/chroma/` (operational — re-index)
  - **Description**: Run `python scripts/indexar_pdfs.py --reset` to delete the existing L2 collection and re-index in cosine space. This is a mandatory one-time migration; `get_or_create_collection` would otherwise return the stale L2 collection.
  - **Acceptance**: `VectorStore().count() > 0` and distances returned are cosine (0–1 range, not L2).
  - **Dependencies**: T1
  - **Est. lines**: 0 (operational)
  - **Commit**: no commit (local data is gitignored)
  - **Risks**: Re-embedding takes ~30s. Must not skip `--reset`.

- [x] **T3 — Create RAG-only system prompt**
  - **Files**: `rag/prompts/chat_prompt.py` (create), `rag/prompts/__init__.py` (modify)
  - **Description**: Create `chat_prompt.py` with `SYSTEM_PROMPT` constant per design (grounding clause, "vos" voice, LaTeX passthrough, out-of-scope refusal). Re-export from `__init__.py`.
  - **Acceptance**: `from rag.prompts import SYSTEM_PROMPT` works; `SYSTEM_PROMPT.format(context="test")` substitutes correctly; prompt contains "No encuentro info sobre esto en los apuntes" fallback clause.
  - **Dependencies**: none
  - **Est. lines**: +21
  - **Commit**: `feat(rag): add RAG-only system prompt with grounding clause`
  - **Risks**: none

## Phase 2: Core Implementation

- [x] **T4 — Create RAG orchestration chain**
  - **Files**: `rag/chain.py` (create)
  - **Description**: Implement `generate_response(query: str) -> Generator[str, None, None]`. Module-level OpenAI singleton (`base_url="https://api.groq.com/openai/v1"`). Flow: embed query → `similarity_search_with_scores` → threshold check (cosine dist > 0.5 → "No encuentro..." without calling Groq) → build prompt with context → `chat.completions.create(stream=True)` → yield SSE frames (`data: <token>\n\n`). Catch all exceptions → yield `event: error\ndata: <msg>\n\n`. Always terminate with `data: [DONE]\n\n`. No module-level mutable per-request state.
  - **Acceptance**: (1) Happy path yields tokens. (2) Out-of-scope query yields single "No encuentro..." + `[DONE]`, Groq never called. (3) Mid-stream Groq error yields `event: error` + `[DONE]`, no raise. (4) No FastAPI imports.
  - **Dependencies**: T1, T3
  - **Est. lines**: +88
  - **Commit**: `feat(rag): add RAG orchestration chain with SSE streaming`
  - **Risks**: Must verify Groq streaming API behavior with `openai` package.

- [x] **T5 — Update requirements.txt**
  - **Files**: `requirements.txt` (modify)
  - **Description**: Add `fastapi`, `uvicorn[standard]`, `openai`. Pin `chromadb==<exact>` (run `pip show chromadb` to get local version). Remove `>=` range on `chromadb`.
  - **Acceptance**: `pip install -r requirements.txt` succeeds; `chromadb` version matches local bake version exactly.
  - **Dependencies**: none (but best done after T4 to know all deps)
  - **Est. lines**: ~5 changed
  - **Commit**: `chore: add fastapi, uvicorn, openai; pin chromadb`
  - **Risks**: Pinning chromadb may conflict with other deps — verify install.

## Phase 3: Transport + Frontend

- [x] **T6 — Create FastAPI app with SSE chat endpoint**
  - **Files**: `app/main.py` (create)
  - **Description**: FastAPI app with: (1) Boot assertion — `GROQ_API_KEY` set or raise with clear message. (2) Boot assertion — `VectorStore().count() > 0` or raise. (3) `ChatRequest(BaseModel)` with `query: str = Field(min_length=1, max_length=500)`. (4) `POST /chat` → `StreamingResponse(generate_response(req.query), media_type="text/event-stream")`. (5) `GET /` serves static files via `StaticFiles` mount. No RAG logic in this file.
  - **Acceptance**: (1) Missing GROQ_API_KEY → uvicorn refuses to start with clear log. (2) Empty ChromaDB → uvicorn refuses to start. (3) `POST /chat` with empty query → 422. (4) `POST /chat` with >500 chars → 422. (5) Valid query → SSE stream. (6) `GET /` → HTML page.
  - **Dependencies**: T4, T5
  - **Est. lines**: +56
  - **Commit**: `feat(app): add FastAPI chat endpoint with boot assertions`
  - **Risks**: none

- [x] **T7 — Create chat frontend (HTML + CSS + JS)**
  - **Files**: `app/static/index.html` (create), `app/static/style.css` (create), `app/static/chat.js` (create)
  - **Description**: Single-page chat UI in Spanish. `chat.js` uses `fetch()` + `ReadableStream` reader (NOT EventSource) per design's SSE client parser contract (7 points: streaming, buffering, frame splitting on `\n\n`, frame dispatch for `data:`/`event: error`/`[DONE]`, re-enable on terminal, null body handling, pre-send validation). `<form>` with `<button type="submit">` for keyboard accessibility. Input disabled while streaming. "Cargando..." indicator on send.
  - **Acceptance**: (1) First load shows empty message list + Spanish placeholder. (2) Send creates assistant bubble, tokens append progressively. (3) "No encuentro..." displays verbatim. (4) `event: error` → "Ocurrió un error, intentá de nuevo" + re-enable. (5) `[DONE]` re-enables input. (6) Empty submit blocked with Spanish hint. (7) Enter key submits.
  - **Dependencies**: T6
  - **Est. lines**: +220
  - **Commit**: `feat(app): add chat frontend with SSE streaming and validation`
  - **Risks**: SSE hand-parsing is the most complex frontend piece; test carefully against real server.

## Phase 4: Deploy Preparation

- [x] **T8 — Create Render pre-bake script**
  - **Files**: `scripts/preparar_indice_render.py` (create)
  - **Description**: Idempotent script that downloads `intfloat/multilingual-e5-small` snapshot to `rag/index/hf-model/` using `huggingface_hub.snapshot_download` (or `SentenceTransformer` first-load with `SENTENCE_TRANSFORMERS_HOME`). Skips if already present.
  - **Acceptance**: First run downloads ~270MB. Second run skips. `rag/index/hf-model/` contains model files.
  - **Dependencies**: T5
  - **Est. lines**: +45
  - **Commit**: `feat(scripts): add HF model pre-bake script for Render deploy`
  - **Risks**: First download is ~270MB; needs network.

- [x] **T9 — Bake ChromaDB index and HF model into repo**
  - **Files**: `rag/index/chroma/` (create, tracked), `rag/index/hf-model/` (create, tracked)
  - **Description**: (1) `rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/` (cosine-space index from T2). (2) `python scripts/preparar_indice_render.py` (downloads HF model to `rag/index/hf-model/`). (3) `git add rag/index/chroma/ rag/index/hf-model/`.
  - **Acceptance**: `rag/index/chroma/` contains ChromaDB files. `rag/index/hf-model/` contains model snapshot. Both tracked by git.
  - **Dependencies**: T2, T8
  - **Est. lines**: 0 reviewable (~270MB binary)
  - **Commit**: `chore: bake ChromaDB index and HF model snapshot for Render`
  - **Risks**: `git add` of ~270MB may take minutes. Verify `.gitignore` does NOT block `rag/index/`.

- [x] **T10 — Create render.yaml and update .env.example**
  - **Files**: `render.yaml` (create), `.env.example` (modify)
  - **Description**: `render.yaml` per design (build: `pip install -r requirements.txt`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, env vars: GROQ_API_KEY sync:false, CHROMA_PERSIST_DIR, HF_HOME, SENTENCE_TRANSFORMERS_HOME, LLM_MODEL, OMP_NUM_THREADS=1, TOKENIZERS_PARALLELISM=false). `.env.example`: add HF_HOME, SENTENCE_TRANSFORMERS_HOME, OMP_NUM_THREADS, TOKENIZERS_PARALLELISM.
  - **Acceptance**: `render.yaml` is valid YAML. `.env.example` documents all new vars.
  - **Dependencies**: T5
  - **Est. lines**: +30
  - **Commit**: `chore(deploy): add render.yaml and update .env.example`
  - **Risks**: none

## Phase 5: Verification

- [x] **T11 — Memory measurement and smoke test**
  - **Files**: none (operational)
  - **Description**: Start `uvicorn app.main:app` locally, send a representative query, measure peak RSS via `ps` or `/proc/self/status`. Record the number. Target: peak < 500MB with `OMP_NUM_THREADS=1` and `TOKENIZERS_PARALLELISM=false`.
  - **Acceptance**: Peak RSS recorded. If < 500MB, pass. If > 500MB, investigate fallbacks per design.
  - **Dependencies**: T6, T7, T9
  - **Est. lines**: 0
  - **Commit**: no commit (measurement only)
  - **Risks**: May need fallback if > 500MB.

- [x] **T12 — End-to-end manual test (Nair demo scenarios)**
  - **Files**: none (operational)
  - **Description**: Run all 8 scenarios from design's Testing Strategy table: happy path, no-context fallback, mid-stream failure (monkey-patch), concurrent requests, boot assertion (missing key), boot assertion (empty ChromaDB), prompt assembly, and full Nair demo (3 in-corpus + 1 out-of-scope question).
  - **Acceptance**: All 8 scenarios pass per design's Testing Strategy table.
  - **Dependencies**: T11
  - **Est. lines**: 0
  - **Commit**: no commit (verification only)
  - **Risks**: Requires valid GROQ_API_KEY and network access.

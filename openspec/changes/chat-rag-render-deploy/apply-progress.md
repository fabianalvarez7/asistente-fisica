# Apply Progress: chat-rag-render-deploy

**Mode**: Standard (strict_tdd: false)
**Chain strategy**: stacked-to-main (resolved preflight)
**PRs**: LOCAL-ONLY — `gh` CLI not installed and no git remote configured.

## Summary

All 12 tasks were implemented and committed across 3 stacked branches. Code-level
acceptance checks pass. Two operational realities diverged from the design
forecast and must be surfaced to Fabián/Nair before deploy:

1. **Full PDF re-index timed out**: marker-pdf OCR is extremely slow on this
   machine. Only 3 of 8 PDFs (25 chunks) finished re-indexing into cosine space.
   The remaining 5 PDFs must be indexed before the demo corpus is complete.
2. **Memory exceeds Render free tier**: measured peak RSS on macOS is ~967 MB
   after the first `/chat` request, far above the 512 MB Render free-tier limit
   and the design's 500 MB target. The design's 270 MB weight estimate was low;
   the actual e5-small bake is 471 MB on disk, and the runtime RSS is larger.

## Branches / PRs

| PR | Branch | Base | Status | Commit count | Notes |
|----|--------|------|--------|--------------|-------|
| PR 1 | `feat/chat-rag-render-deploy-pr1` | `main` | LOCAL-ONLY, committed | 4 | RAG chain foundation |
| PR 2 | `feat/chat-rag-render-deploy-pr2` | `feat/chat-rag-render-deploy-pr1` | LOCAL-ONLY, committed | 6 | FastAPI + frontend (includes PR 1 commits) |
| PR 3 | `feat/chat-rag-render-deploy-pr3` | `feat/chat-rag-render-deploy-pr2` | LOCAL-ONLY, committed | 8 | Deploy + bake + verification (includes PR 1/2 commits) |

Because `gh` is not installed and no remote is configured, branches exist only
locally. Fabián must push them and open PRs manually, or run `gh pr create`
after installing the GitHub CLI and configuring a remote.

## Task Completion

- [x] **T1** — Extend VectorStore with `similarity_search_with_scores`
- [x] **T2** — Migrate local ChromaDB to cosine space (PARTIAL: 3/8 PDFs, 25 chunks)
- [x] **T3** — Create RAG-only system prompt
- [x] **T4** — Create RAG orchestration chain
- [x] **T5** — Update requirements.txt
- [x] **T6** — Create FastAPI app with SSE chat endpoint
- [x] **T7** — Create chat frontend (HTML + CSS + JS)
- [x] **T8** — Create Render pre-bake script
- [x] **T9** — Bake ChromaDB index and HF model into repo
- [x] **T10** — Create render.yaml and update .env.example
- [x] **T11** — Memory measurement and smoke test (completed, result over budget)
- [x] **T12** — End-to-end manual test (partial, missing GROQ_API_KEY)

## Per-Task Verification

| Task | Check | Result | Notes |
|------|-------|--------|-------|
| T1 | `VectorStore().count()` returns 25 | PASS | Cosine metadata committed; new method returns `[(doc, dist)]` |
| T1 | `similarity_search()` unchanged | PASS | Existing callers still work |
| T2 | Collection metadata `hnsw:space: cosine` | PASS | --reset executed; distances in 0–1 range |
| T2 | All 8 PDFs re-indexed | FAIL/TIMEOUT | Only 3 PDFs completed; marker-pdf OCR too slow |
| T3 | `from rag.prompts import SYSTEM_PROMPT` | PASS | Re-export works |
| T3 | `SYSTEM_PROMPT.format(context="test")` | PASS | Substitution works; fallback clause present |
| T4 | No FastAPI imports in `rag/chain.py` | PASS | Verified via introspection |
| T4 | `generate_response` is generator | PASS | Verified |
| T4 | Mid-stream error → `event: error` + `[DONE]` | PASS | Monkey-patched client raised; output correct |
| T4 | Happy path yields tokens | SKIP | Requires valid `GROQ_API_KEY` |
| T5 | `pip install -r requirements.txt` succeeds | PASS | fastapi installed; chromadb==1.5.9 matches |
| T6 | Missing `GROQ_API_KEY` → clear error + exit | PASS | RuntimeError raised at import |
| T6 | Empty ChromaDB → clear error + exit | PASS | RuntimeError raised |
| T6 | `ChatRequest(query="")` → ValidationError | PASS | 422 on endpoint |
| T6 | `ChatRequest(query="x"*501)` → ValidationError | PASS | 422 on endpoint |
| T6 | `GET /` returns 200 | PASS | Served via StaticFiles mount |
| T7 | Static assets served | PASS | `/style.css`, `/chat.js` return 200 |
| T7 | Pre-send validation (empty/>500) | PASS | Spanish hints shown, no fetch |
| T7 | SSE parser 7-point contract | PASS | Reviewed implementation; error + DONE frames handled |
| T8 | First run downloads model | PASS | Downloaded to `rag/index/hf-model/` |
| T8 | Second run skips | PASS | Snapshot detected, no re-download |
| T9 | `rag/index/chroma/` tracked | PASS | Copied from `data/chroma/` |
| T9 | `rag/index/hf-model/` tracked | PASS | 471 MB of HF cache committed |
| T10 | `render.yaml` valid YAML | PASS | Parsed with `yaml.safe_load` |
| T10 | `.env.example` documents new vars | PASS | HF_HOME, SENTENCE_TRANSFORMERS_HOME, OMP_NUM_THREADS, TOKENIZERS_PARALLELISM added |
| T11 | Peak RSS recorded | PASS | Boot ~464 MB; after first `/chat` ~967 MB (CPU device) |
| T11 | Peak < 500 MB | FAIL | 967 MB >> 500 MB; see Risks |
| T12 | No-context fallback path | PASS | Verified by forcing threshold low |
| T12 | Prompt assembly | PASS | SYSTEM_PROMPT formatted with retrieved context |
| T12 | Mid-stream failure | PASS | Already covered in T4 |
| T12 | Concurrent requests | PASS | 3 simultaneous `httpx` requests returned independent error streams |
| T12 | Boot assertion missing key | PASS | Covered in T6 |
| T12 | Boot assertion empty ChromaDB | PASS | Covered in T6 |
| T12 | Happy path / Nair demo | SKIP | Requires valid `GROQ_API_KEY` |

## Files Changed

| File | Action | PR |
|------|--------|-----|
| `rag/retrievers/vector_store.py` | Modified | PR 1 |
| `rag/prompts/chat_prompt.py` | Created | PR 1 |
| `rag/prompts/__init__.py` | Modified | PR 1 |
| `rag/chain.py` | Created | PR 1 |
| `requirements.txt` | Modified | PR 1 |
| `app/main.py` | Created | PR 2 |
| `app/static/index.html` | Created | PR 2 |
| `app/static/style.css` | Created | PR 2 |
| `app/static/chat.js` | Created | PR 2 |
| `scripts/preparar_indice_render.py` | Created | PR 3 |
| `rag/index/chroma/` | Created (tracked) | PR 3 |
| `rag/index/hf-model/` | Created (tracked) | PR 3 |
| `render.yaml` | Created | PR 3 |
| `.env.example` | Modified | PR 3 |

## Deviations from Design

1. **Partial re-index (T2)**: The design assumed `scripts/indexar_pdfs.py --reset`
   would re-index all 8 PDFs quickly. On this machine marker-pdf OCR averaged
   ~8–23 minutes per PDF; after ~70 minutes only 3 PDFs finished. The baked
   ChromaDB index contains 25 chunks from those 3 PDFs instead of the expected
   19-chunk full corpus. Fabián must finish indexing the remaining PDFs before
   the demo.

2. **HF bake size (T8/T9)**: The design forecast ~270 MB for the model. The
   actual `SentenceTransformer` first-load bake is 471 MB on disk (model
   safetensors ~449 MB + tokenizer + sentencepiece). The original
   `huggingface_hub.snapshot_download` approach downloaded 2.1 GB because it
   included pytorch, onnx, and openvino copies; the script was amended to use
   `SentenceTransformer` to avoid those duplicates.

3. **Memory over budget (T11)**: Measured peak RSS is ~967 MB on macOS (CPU
   device, `OMP_NUM_THREADS=1`, `TOKENIZERS_PARALLELISM=false`). This is
   materially above the 512 MB Render free-tier limit and the design's 500 MB
   target. No silent fallback was applied; the number is surfaced here.

## Risks for the Orchestrator / Fabián

- **Render free-tier OOM likely**: With 471 MB of model weights on disk and a
  measured peak RSS near 1 GB locally, the app is expected to OOM on Render's
  512 MB container. Mitigations to evaluate before deploying:
  - Verify the measurement on Linux (macOS RSS counts memory-mapped files more
    aggressively; Linux RSS may be lower).
  - Test a smaller multilingual embedding model if Spanish quality allows.
  - Consider Render's paid tier or another host with ≥1 GB RAM.
- **Incomplete corpus**: Only 3 PDFs are in the baked index. Out-of-scope
  detection (cosine threshold) will be unreliable until the remaining PDFs are
  indexed.
- **No PRs opened**: `gh` CLI is missing and no remote is configured. Branches
  are local only.
- **No GROQ_API_KEY in environment**: Happy-path and Nair demo tests were not
  run. Fabián must set a valid key to run T12 fully.

## Recommended Next Steps

1. Obtain `GROQ_API_KEY` and run the happy-path + Nair demo tests.
2. Finish indexing the remaining 5 PDFs with `python scripts/indexar_pdfs.py`
   (no `--reset`, to preserve the 25 already-indexed chunks).
3. Re-run `rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/` and
   amend/replace the T9 commit.
4. Re-measure RSS on a Linux environment closer to Render.
5. Decide on memory mitigation (smaller model or larger host) before public
   deploy.
6. Push branches and open the 3 PRs manually.

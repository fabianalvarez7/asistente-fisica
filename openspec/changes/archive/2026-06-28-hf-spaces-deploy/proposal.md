# Proposal: Migrate Deploy Target to Hugging Face Spaces

## Intent

Render free tier can't host the prototype: measured peak RSS **~967 MB**, 455 MB over the 512 MB cap. Migrate to **Hugging Face Spaces Docker** (free cpu-basic: 16 GB RAM, 2 vCPU, 50 GB disk, ~48 h sleep). Also re-bake ChromaDB with `cuadernillo-fisica-1.pdf` — current index has stale chunks.

## Scope

### In Scope
- Deploy target: Render → HF Spaces Docker
- Re-bake ChromaDB with `cuadernillo-fisica-1.pdf`
- Update `AGENTS.md` §7/§12, `README.md`
- Drop `render.yaml`; add `Dockerfile` + Space `README.md`
- Rename `scripts/preparar_indice_render.py` → `scripts/preparar_indice_hf.py`

### Out of Scope
- Pushing 3 stacked branches from prior change
- `gh` CLI or git remote config
- Re-baking HF model snapshot (done; 471 MB)
- Nair demo (orthogonal; needs `GROQ_API_KEY`)
- Backend changes (`app/main.py`, `rag/chain.py`, prompts, VectorStore)

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `render-deploy`: target changes to HF Spaces Docker. Spec requirements unchanged. Rename to `hf-spaces-deploy` in archive.

## Approach

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Platform | HF Spaces Docker (free cpu-basic) | 16 GB RAM, 48 h sleep, free |
| Pre-bake | Full commit to Space repo | No network dependency; HF supports LFS |
| Port | `--port 7860` in Dockerfile CMD | `app/main.py` doesn't read `$PORT` |
| Corpus | `indexar_pdfs.py --reset` on cuadernillo | Current index stale |
| LFS | `git lfs track rag/index/hf-model/**` | Required for files >10 MB |

## Trade-offs

- **Two repos** (GitHub + HF): accepted. HF is deploy-only.
- **471 MB model via LFS**: accepted. `preload_from_hub` breaks `HF_HOME`.
- **Ephemeral disk wiped on sleep**: accepted. Pre-bakes in git survive.
- **CPU-only torch**: pin via `--extra-index-url`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Git LFS push fails | Low | HF has LFS default; test first |
| Docker build timeout | Medium | CPU-only torch; move marker-pdf to dev deps |
| Stale chunks until re-bake | Certain | Re-bake in-scope; finish before demo |

## Rollback

Delete `Dockerfile` + Space `README.md`. Restore `render.yaml`. Revert docs and script rename. Pre-baked artifacts stay.

## Dependencies

- HF account (free)
- `git lfs` installed
- `GROQ_API_KEY` as Space Secret
- Corpus re-bake before demo

## Success Criteria

- [ ] Docker build succeeds locally
- [ ] Container serves chat at `localhost:7860`
- [ ] Space deploys on HF without OOM
- [ ] Test question returns RAG-grounded response
- [ ] Baked index has cuadernillo chunks only

## Open Questions

- **O1**: Space name/visibility?
- **O2**: GitHub ↔ HF sync (manual vs CI)?
- **O3**: Build time on HF?

## References

- `openspec/changes/deploy-hf-spaces/explore.md`
- `openspec/changes/chat-rag-render-deploy/apply-progress.md`
- [HF Spaces Docker](https://huggingface.co/docs/hub/spaces-sdks-docker)
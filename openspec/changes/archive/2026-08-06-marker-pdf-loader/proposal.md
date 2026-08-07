# Proposal: marker-pdf-loader

## Intent

The Socratic layer cannot guide a student through a formula it cannot read. Obs #163 shows `pymupdf4llm` recovers **zero** LaTeX formulas from clean typeset Sears content (25 pages), while `marker-pdf` recovers 559 at 1.7 min/page on Mac MPS. Obs #164 confirms retrieval scores are identical between extractors, but marker's chunks contain readable LaTeX while pymupdf4llm's contain garbled text. The Socratic layer — the project's priority (AGENTS §8) — depends on this.

## Scope

### In Scope
- Swap `pymupdf4llm` for `marker-pdf` in `rag/loaders/pdf_loader.py`, same `load_pdf(path) -> list[Document]` signature.
- Uncomment `marker-pdf` in `requirements.txt`.
- Re-index the 5 PDFs in `data/pdfs/` into `data/chroma/`.
- Re-bake deploy artifact at `rag/index/chroma/`.
- Smoke test: 2–3 queries confirm LaTeX in chunks.

### Out of Scope
- Socratic prompt, chat UI, embedding model, splitter, dashboard, API.
- Hybrid loader. Mathpix or docling (rejected in obs #163).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `corpus-rebake`: loader swap changes bake pipeline; corpus expands from 1 to 5 PDFs; re-bake runtime increases to ~3–4h.

## Approach

- `pdf_loader.py` uses `marker.converters.PdfConverter` singleton, `disable_image_extraction=True`, same `Document` shape.
- Uncomment `marker-pdf>=1.0` in `requirements.txt`.
- `scripts/indexar_pdfs.py --reset` on 5 PDFs (splitter downstream, unchanged).
- `scripts/preparar_indice_hf.py` re-bakes `rag/index/chroma/`.
- Extend `scripts/run_socratic_tests.py` to assert `$`/`$$` in chunks.

## Affected Areas

- `rag/loaders/pdf_loader.py` — loader swap, singleton converter
- `requirements.txt` — uncomment marker-pdf
- `data/chroma/` — re-indexed (gitignored)
- `rag/index/chroma/` — re-baked (committed)
- `scripts/run_socratic_tests.py` — LaTeX assertion
- `docs/hf-space.md` — marker cache and cold-start docs

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| marker-pdf hangs (ADR 0001) | Med | Smoke-test cuadernillo first (5 pages, ~5 min) |
| Re-index ~3–4h blocks iteration | Med | Background run; only on corpus change |
| marker cache (~3 GB) not in Docker image | High | Extend `preparar_indice_hf.py` or set cache env in Dockerfile |
| Cold-start latency increase | Low | Within existing ~20–40s budget |

## Rollback Plan

Revert `pdf_loader.py`, re-comment `marker-pdf`, re-run `indexar_pdfs.py --reset`, re-bake `rag/index/chroma/`. Single-file revert plus re-index.

## Dependencies

None external. marker-pdf already listed (commented) in `requirements.txt`.

## Open Questions

1. **marker cache on HF Spaces** — `preparar_indice_hf.py` bakes the embedding model to `rag/index/hf-model/` but marker caches at `~/Library/Caches/datalab/models/`. Design must resolve: extend the script or set cache env in Dockerfile.
2. **Canonical corpus** — confirm the 5 PDFs in `data/pdfs/` are complete.

## Success Criteria

- [ ] `pdf_loader.py` uses marker-pdf, same `Document` shape.
- [ ] `requirements.txt` lists `marker-pdf` uncommented.
- [ ] `data/chroma/` rebuilt from 5 PDFs with LaTeX chunks.
- [ ] `rag/index/chroma/` rebuilt and committed.
- [ ] Smoke test: 2–3 queries return chunks with `$`/`$$`.

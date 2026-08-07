# Apply Progress: marker-pdf-loader

**Change**: marker-pdf-loader
**Session**: 2026-08-06 resume
**Mode**: Standard (Strict TDD: false, no test framework installed)

## Goal

Retomar el SDD change `marker-pdf-loader` (swap pymupdf4llm → marker-pdf) en `asistente-fisica`. La sesión pasada murió con el sub-agent de sdd-apply por un re-bake de 3-4h. Esta sesión: aplicar el strategy de "sub-agents chicos + re-bake manual" para llegar al final del apply phase.

## Instructions

- Idioma: rioplatense cálido y directo, voseo
- Modo SDD: auto / openspec / ask-on-risk / 400 líneas (re-confirmado en esta sesión)
- Estrategia apply: partido en 3 batches — (1) pre-re-bake, (2a) paralelo al re-bake, (2b) post-re-bake
- El usuario corre el re-bake de marker-pdf manualmente con `nohup` (5-7h, no 3-4h como decía el design)
- Fabián es el único dev. HF Spaces Docker cpu-basic 16GB. SQLite + ChromaDB.

## Discoveries

- **El sub-agent `sdd-apply` corre bien con scope acotado.** La sesión pasada murió con un solo apply phase largo. En esta sesión, 3 sub-agents chicos (batch 1: 3 tasks, batch 2a: 4 tasks) sobrevivieron sin problema. Confirmado: partir apply en batches por gate de humano es la forma.
- **El timeout del smoke test del cuadernillo era 10 min, pero el design estimaba 11.5 min.** El primer retry murió a 7.5 min con la primera "Recognizing Text" en curso. Retry con timeout 25 min pasó en 10.9 min. Lección: cuando el design da una estimación, darle 2x de headroom en timeouts.
- **El ETA real del re-bake es 5-7h, no 3-4h.** El `Recognizing Text: 1/299 [90.79s/it]` significa que marker procesa 299 BLOQUES de texto (no páginas) a ~90s/bloque. Para 5 PDFs esto da 7.5h. La estimación anterior (43 min para Cinemática 1) parece haber sido con otro sample o setup.
- **Env var crítico: marker-pdf 1.10.2 / surya-ocr 0.11.8 lee `MODEL_CACHE_DIR`, NO `SURYA_MODEL_CACHE_DIR`.** El design.md tenía el nombre viejo. Si no se corregía, el Space re-descargaba ~3GB en cada cold start. Sub-agent lo verificó y corrigió. Guardado en Engram obs #177.
- **El `sdd-status` dispatcher no detecta `spec.md` cuando está en la raíz del change dir** — espera subdir `specs/`. No bloqueó el flujo porque los archivos reales son la verdad, pero el status JSON miente.

## Accomplished

- ✅ SDD Session Preflight re-confirmado (auto / openspec / ask-on-risk / 400 líneas), guardado obs #173
- ✅ Estrategia apply-batcheada decidida y guardada (obs #172)
- ✅ **Batch 1 apply (3 tasks):** tasks 1.3 (smoke test cuadernillo, 10.9 min OK), 2.1 (canonicity gate), 2.2 (verify_latex.py) — commits d876021, 8b3d6c3
- ✅ **Batch 2a apply (4 tasks, paralelo al re-bake):** tasks 3.1 (Dockerfile marker bake con `MODEL_CACHE_DIR`), 3.3 (docstring preparar_indice_hf.py), 3.4 (docs/hf-space.md re-bake section), 4.1 (formula retrieval smoke test) — commits 42eef80, eb5131d, 5afd167, ad96f9c
- ✅ **Batch 2b apply (4 tasks, post-re-bake):** tasks 2.4 (run verify_latex.py: PASS 2665 ≥ 2000), 3.2 (cp bake a rag/index/chroma, commit 2e692be), 4.2 (socratic smoke 26/26 PASS, formula retrieval PASS), 4.3 (backward-compat: no pymupdf4llm, env vars correctos)
- ✅ 9 commits totales en main para el change
- ✅ Re-bake manual del usuario: `nohup python scripts/indexar_pdfs.py --reset > /tmp/marker-rebake.log 2>&1 &`, PID 62643, terminó con 1374 chunks, 0 errores
- ✅ Design.md reconciliado con sección "## Implementation Reconciliation" (W-1, W-2, W-6 del verify)

## Workload / PR Boundary

- Mode: single PR (ask-on-risk, ~213 LOC code + 12 MB binary bake, all under 400-line code budget)
- Commits: 9 work-unit commits + 1 archive commit = 10 total
- Binary commit (`2e692be`): 12 MB, well under 100 MB Git-LFS cap

## Engram observation IDs

- `sdd-preflight/marker-pdf-loader-2026-08-06` (obs #173): preflight decisions
- `marker-pdf-loader/apply-strategy` (obs #172): 3-batch strategy
- `marker-pdf-loader/env-var-correction` (obs #177): MODEL_CACHE_DIR fix
- `marker-pdf-loader/rebake-result` (obs #179): 1374 chunks, 0 errors
- `marker-pdf-loader/design-reconciliation` (obs #182): design.md edits

## Next Steps (post-archive)

1. `sdd-verify marker-pdf-loader` (delegado a fresh-context reviewer)
2. `sdd-archive marker-pdf-loader` + push + PR
3. (Optional) W-3 follow-up: add per-chapter ≥400 floor to `verify_latex.py`
4. (Optional) W-4 follow-up: make `test_formula_retrieval()` fatal in `run_socratic_tests.py`

## Relevant Files

- `openspec/changes/marker-pdf-loader/{proposal,spec,design,tasks}.md` — planning artifacts
- `rag/loaders/pdf_loader.py` — commit 1e3785f (marker-pdf singleton, removió pymupdf4llm)
- `requirements.txt` — commit c145805 (marker-pdf>=1.10, drop pymupdf4llm)
- `scripts/indexar_pdfs.py` — commit d876021 (canonicity gate, 5-PDF check)
- `scripts/verify_latex.py` — commit 8b3d6c3 (asserts ≥2000 LaTeX)
- `Dockerfile` — commit 42eef80 (marker-pdf/surya model bake, MODEL_CACHE_DIR)
- `scripts/preparar_indice_hf.py` — commit eb5131d (docstring explicativo)
- `docs/hf-space.md` — commit 5afd167 (re-bake section para 5-PDF marker-pdf)
- `scripts/run_socratic_tests.py` — commit ad96f9c (formula retrieval smoke test)
- `rag/index/chroma/` — commit 2e692be (12 MB bake, 1374 chunks)
- `data/chroma/` — fresh re-bake (not committed, dev only)
- `/tmp/marker-rebake.log` — log del re-bake

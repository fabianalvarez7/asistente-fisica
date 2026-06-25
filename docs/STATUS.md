# Status — Asistente de Física

> Snapshot del estado del proyecto. Última actualización: cierre de semana 1-2 (2026-06-25).

## Semana 1-2: Cerrada ✅

### Lo que se construyó

- ✅ **Setup del repo** (Día 1): estructura de carpetas, `requirements.txt`, `.gitignore`, `.env.example`, venv con MPS verificado. Commit `4d0aeb7`.
- ✅ **PDF loader con marker-pdf** (Día 2-3): wrapper en `rag/loaders/pdf_loader.py`, singleton de modelos, `disable_image_extraction=True`. Commit `45e2ce0` + ADR 0001.
- ✅ **Pipeline RAG end-to-end** (Día 4-5): splitter, embeddings, ChromaDB persistente, script de indexación idempotente. Commit `f3daf3e`.
- ✅ **Indexación del cuadernillo** (única fuente en el corpus actual): 19 chunks, dim 384, persistido en `data/chroma/`.

### Corpus actual

| PDF | Estado | Razón |
|---|---|---|
| `cuadernillo-fisica-1.pdf` | ✅ Indexado | Único PDF con texto limpio y fórmulas en LaTeX embebidas |
| `01-clase-26-03-2025.pdf` | ❌ Pendiente | Aceptable, pero escaneado/parcial |
| `04-clase-09-04-2025.pdf` | ❌ Descartado | Escaneo puro, OCR alucina |
| `05-cinematica-2d.pdf` | ❌ Descartado | Mezcla de escaneo y fotos a mano |
| `06-dinamica.pdf` | ❌ Descartado | Mezcla de escaneo y fotos a mano |
| `07-movimiento-circular.pdf` | ❌ Descartado | Mezcla de escaneo y fotos a mano |
| `08-torque.pdf` | ❌ Descartado | Mezcla de escaneo y fotos a mano |
| `09-energia.pdf` | ❌ Descartado | Mezcla de escaneo y fotos a mano |

**Decisión**: el prototipo inicial solo cubre Teoría de Errores (cuadernillo). Para expandir el corpus, Nair debe proveer versiones con texto seleccionable de las clases (Word, LaTeX, PDF de libro digital).

### Validación

- 8 queries de prueba ejecutadas contra el cuadernillo indexado.
- 6/8 queries devolvieron el chunk esperado en top-1.
- Caso destacado: "¿Qué variable se usa para el error relativo porcentual?" → `$$Er_X = \frac{\Delta X}{X'} \tag{3}$$` como top hit.
- Tiempo end-to-end: 12 min para el cuadernillo (708s marker + 8s embeddings + 0.17s store).

## Decisiones arquitectónicas tomadas

- **ADR 0001**: PDF loader migrado de pymupdf4llm a marker-pdf para rescatar fórmulas en LaTeX. Ver `docs/adr/0001-pdf-loader-marker.md`.

## Lo que falta (roadmap)

| Semana | Milestone | Estado |
|---|---|---|
| 1-2 | Setup + RAG base en terminal | ✅ Cerrado |
| 3-4 | FastAPI + chat HTML, primer deploy a Render | 🔜 Siguiente |
| 5-6 | Capa Socrática (prompts + few-shot), historial en SQLite, identificación básica | Pendiente |
| 7-8 | Polish, iteración con Nair, segunda demo | Pendiente |
| 9-10 | Dashboard Streamlit (opcional, primer candidato a cut) | Pendiente |
| 11-12 | Deploy final, polish, demo final | Pendiente |

Ver `AGENTS.md` sección 8 para el roadmap completo.

## Próximo paso concreto

**Día 6-7**: crear `scripts/query.py` — script de consulta en terminal que toma una pregunta y devuelve los top-k chunks. RAG puro, sin LLM todavía.

Comando esperado:
```bash
python scripts/query.py "¿Cuál es la fórmula del error relativo?"
```

Output esperado:
```
Top 3 chunks más relevantes:

[1] score=0.87 | fuente=cuadernillo-fisica-1.pdf
    ...contenido del chunk...

[2] score=0.81 | ...
[3] score=0.78 | ...
```

## Gotchas conocidos

Ver `docs/gotchas.md` para la lista completa. Los más relevantes ahora:

- **marker tarda ~10 min para 5 páginas en Mac con MPS**. Una sola vez por corpus.
- **marker NO maneja bien PDFs escaneados puros** (alucinaciones). Material con texto seleccionable es obligatorio.
- **MPS parcial**: `TableRecEncoderDecoderModel` no soporta MPS, cae a CPU. Esto explica parte de la lentitud.
- **Versiones modernas**: langchain 1.3, chromadb 1.5, sentence-transformers 5.6 — la API difiere de tutoriales viejos.

## Comandos útiles

```bash
# Indexar (idempotente)
python scripts/indexar_pdfs.py

# Re-indexar desde cero
python scripts/indexar_pdfs.py --reset

# Indexar un solo PDF
python scripts/indexar_pdfs.py --pdf data/pdfs/cuadernillo-fisica-1.pdf

# Probar retrieval manualmente (próximamente en Día 6-7)
python scripts/query.py "¿Qué es la energía cinética?"

# Ver logs de git
git log --oneline
```

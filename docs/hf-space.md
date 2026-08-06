# Guía de deploy en Hugging Face Spaces

Esta plantilla sirve para crear el Space `fabianalvarez/asistente-fisica` (público, Docker SDK).

## Qué copiar al repo del Space

El Space es un repo separado del repo de GitHub. Solo necesita estos archivos:

```text
.
├── Dockerfile
├── README.md          # este archivo, con el YAML header de abajo
├── requirements.txt
├── app/
├── rag/
│   ├── chain.py
│   ├── prompts/
│   ├── retrievers/
│   ├── loaders/
│   ├── splitters/
│   └── index/
│       └── chroma/    # índice pre-bakeado (git normal, ~500 KB)
└── scripts/
```

> El modelo de embeddings **no se copia** al repo del Space. El Dockerfile lo descarga en build time usando `scripts/preparar_indice_hf.py`. Trackearlo vía Git LFS no es viable: GitHub LFS free tier limita archivos a 100 MB y el modelo pesa 448 MB.
>
> Los modelos de marker-pdf/surya (~3.5 GB) **tampoco se copian**. El Dockerfile los descarga en build time mediante `create_model_dict()` y `MODEL_CACHE_DIR`. Ver "Re-bakear el corpus" abajo.

## Plantilla de README.md para el Space

Copiar exactamente este bloque al inicio del `README.md` del Space:

```markdown
---
title: Asistente de Física 1
emoji: 🧲
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Asistente de Física 1

Asistente Socrático de Física 1 — UNR (Bioquímica y Farmacia).
Responde preguntas de física usando los apuntes del curso.
Funciona con RAG (ChromaDB + multilingual-e5-small) y Groq (LLM).
```

## Pasos de deploy manual

1. En HF Hub, crear un Space nuevo:
   - Owner: `fabianalvarez`
   - Name: `asistente-fisica`
   - SDK: `Docker`
   - Visibility: `Public`
2. Clonar el repo del Space.
3. Copiar desde el repo de GitHub:
   - `Dockerfile`, `requirements.txt`
   - `app/`, `rag/` (incluyendo `rag/index/chroma/`, **sin** `rag/index/hf-model/`)
4. En el repo del Space:

   ```bash
   git add .
   git commit -m "deploy: asistente-fisica"
   git push
   ```

> El primer build tarda más de lo normal (~3-5 min extra) porque el Dockerfile descarga el modelo de embeddings. Los rebuilds siguientes lo reutilizan del cache de capas.

5. En la UI del Space, ir a **Settings → Secrets** y agregar `GROQ_API_KEY`.
6. Esperar el build y probar la URL pública.

## Re-bakear el corpus

Cuando cambie el corpus (PDFs o parámetros de chunking), regenerar el índice desde cero:

```bash
# 1. Re-indexar los 5 PDFs canónicos (tarda ~5-7 h en Mac MPS; es normal).
python scripts/indexar_pdfs.py --reset

# 2. Verificar que marker-pdf recuperó fórmulas en LaTeX antes de seguir.
python scripts/verify_latex.py

# 3. Copiar el índice local al artefacto bakeado que se commitea.
rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/

# 4. Commitear y subir.
git add rag/index/chroma/
git commit -m "chore(data): rebake chroma index (marker-pdf, 5 PDFs)"
git push
```

Luego volver a copiar `rag/index/chroma/` al repo del Space y hacer push.

> Los modelos de marker-pdf se hornean en la imagen de Docker (no en el repo) mediante `create_model_dict()` durante el build. Esto evita que el Space los descargue en cada cold-start, manteniendo el primer request dentro del presupuesto de ~20-40 s.

## Variables y secretos

| Variable | Dónde va | Notas |
|----------|----------|-------|
| `GROQ_API_KEY` | HF Space Secret | Única variable sensible. |
| `CHROMA_PERSIST_DIR` | `Dockerfile` ENV | `./rag/index/chroma` en el Space. |
| `HF_HOME` | `Dockerfile` ENV | `./rag/index/hf-model`. |
| `SENTENCE_TRANSFORMERS_HOME` | `Dockerfile` ENV | Igual que `HF_HOME`. |
| `MODEL_CACHE_DIR` | `Dockerfile` ENV | `./rag/index/marker-models` (modelos de marker-pdf/surya). |
| `TORCH_DEVICE_MODEL` | `Dockerfile` ENV | `cpu` en el Space; las Mac/Windows usan auto. |
| `LLM_MODEL` | `Dockerfile` ENV | `llama-3.3-70b-versatile`. |
| `OMP_NUM_THREADS` | `Dockerfile` ENV | `1` para no saturar la CPU. |
| `TOKENIZERS_PARALLELISM` | `Dockerfile` ENV | `false` para estabilidad de memoria. |

## Rollback

Si algo falla, se puede restaurar `render.yaml` desde el historial de git y borrar los archivos de HF Spaces:

```bash
git checkout main -- render.yaml
rm -f Dockerfile .gitattributes docs/hf-space.md
# (restaurar también AGENTS.md, README.md, .env.example si se editaron)
```

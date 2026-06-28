# Guía de deploy en Hugging Face Spaces

Esta plantilla sirve para crear el Space `fabianalvarez/asistente-fisica` (público, Docker SDK).

## Qué copiar al repo del Space

El Space es un repo separado del repo de GitHub. Solo necesita estos archivos:

```text
.
├── Dockerfile
├── .gitattributes
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
│       ├── chroma/    # índice pre-bakeado (git normal)
│       └── hf-model/  # modelo vía Git LFS
└── scripts/
```

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
   - `Dockerfile`, `.gitattributes`, `requirements.txt`
   - `app/`, `rag/` (incluyendo `rag/index/chroma/` y `rag/index/hf-model/`)
4. En el repo del Space:

   ```bash
   git lfs install
   git add .
   git commit -m "deploy: asistente-fisica"
   git push
   ```

5. En la UI del Space, ir a **Settings → Secrets** y agregar `GROQ_API_KEY`.
6. Esperar el build y probar la URL pública.

## Re-bakear el corpus

Cuando cambie el PDF o los parámetros de chunking:

```bash
python scripts/indexar_pdfs.py --reset --pdf data/pdfs/cuadernillo-fisica-1.pdf
rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/
git add rag/index/chroma/
git commit -m "chore(data): rebake chroma index"
```

Luego volver a copiar `rag/index/chroma/` al repo del Space y hacer push.

## Variables y secretos

| Variable | Dónde va | Notas |
|----------|----------|-------|
| `GROQ_API_KEY` | HF Space Secret | Única variable sensible. |
| `CHROMA_PERSIST_DIR` | `Dockerfile` ENV | `./rag/index/chroma` en el Space. |
| `HF_HOME` | `Dockerfile` ENV | `./rag/index/hf-model`. |
| `SENTENCE_TRANSFORMERS_HOME` | `Dockerfile` ENV | Igual que `HF_HOME`. |
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

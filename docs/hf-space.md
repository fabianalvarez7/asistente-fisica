# Guía de deploy en Hugging Face Spaces

El Space activo es **`fabianalvarez7/asistente-fisica-unr`** (público, Docker SDK, cpu-basic). Es un mirror del repo de GitHub con un commit adicional que pre-crea `/app/data` para que SQLite funcione (commit `f4eace8` en el Space; misma lógica que `87ed3fd` en el source).

> ⚠️ **Crear un Space nuevo en HF requiere suscripción PRO** ($9/mes). La API devuelve `402 Payment Required` si el usuario no es PRO. Esto aplica solo a la **creación**; redeployar a un Space existente es gratis y funciona sin PRO. Confirmado en 2026-08-07: el plan free alcanza para el redeploy pero no para crear uno nuevo.

## Qué copiar al repo del Space

El Space es un repo separado del repo de GitHub. Los archivos tracked son los mismos que el source, **excepto** los artefactos de dev (ver "Excluir del sync" abajo). El bake de ChromaDB es ~12 MB y se trackea vía LFS en el Space (migrado automáticamente a xet storage por HF, ver "Pushing binary files" abajo).

```text
.
├── Dockerfile
├── README.md          # este archivo, con el YAML header de abajo
├── requirements.txt
├── .gitattributes     # tracking LFS para *.bin, *.sqlite3, *.pickle
├── app/
├── rag/
│   ├── chain.py
│   ├── prompts/
│   ├── retrievers/
│   ├── loaders/
│   ├── splitters/
│   └── index/
│       └── chroma/    # bake de ChromaDB (12 MB, LFS-tracked en el Space)
└── scripts/
```

> El modelo de embeddings **no se copia** al repo del Space. El Dockerfile lo descarga en build time (cacheado en `rag/index/hf-model/`, que es gitignored).
>
> Los modelos de marker-pdf/surya (~3.5 GB) **tampoco se copian**. El Dockerfile los descarga en build time mediante `create_model_dict()` y `MODEL_CACHE_DIR=/app/rag/index/marker-models`. Ver "Re-bakear el corpus" abajo.

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

## Pasos de deploy manual (creación inicial — solo si NO existe el Space)

⚠️ Requiere PRO. Si el Space ya existe (caso nuestro), salta a "Workflow de redeploy" abajo.

1. En HF Hub, crear un Space nuevo:
   - Owner: `fabianalvarez7`
   - Name: `asistente-fisica-unr`
   - SDK: `Docker`
   - Visibility: `Public`
2. Clonar el repo del Space.
3. Copiar desde el repo de GitHub:
   - `Dockerfile`, `requirements.txt`, `.gitattributes`, `README.md`
   - `app/`, `rag/` (incluyendo `rag/index/chroma/`, **sin** `rag/index/hf-model/`)
   - `scripts/`
4. En el repo del Space:

   ```bash
   git add .
   git commit -m "deploy: asistente-fisica"
   git push
   ```

> El primer build tarda más de lo normal (~3-5 min extra) porque el Dockerfile descarga el modelo de embeddings. Los rebuilds siguientes lo reutilizan del cache de capas.

5. En la UI del Space, ir a **Settings → Secrets** y agregar `GROQ_API_KEY`.
6. Esperar el build y probar la URL pública.

## Workflow de redeploy (rebuild con código nuevo)

El patrón que se usa desde mediados de 2025: cada vez que cambia algo en el source, se hace un "redeploy" al Space. Esto es gratis y no requiere PRO.

```bash
# 0. Asegurarse de tener el código actualizado y comiteado en el source (en GitHub).
cd /Users/fabianalvarez/Documents/TUIA/asistente-fisica
git log --oneline -3  # ver los commits que aún no están en el Space

# 1. Clonar el Space en /tmp (solo la primera vez, después se puede reusar).
export HF_TOKEN=hf_...  # token con scope de escritura
rm -rf /tmp/asistente-fisica-space
git clone https://fabianalvarez7:${HF_TOKEN}@huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr /tmp/asistente-fisica-space

# 2. Sincronizar archivos del source al Space (con excludes para no inflar el deploy).
rsync -av --delete \
  --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.DS_Store' --exclude='.git' \
  --exclude='data/' --exclude='.pytest_cache' --exclude='.mypy_cache' \
  --exclude='rag/index/hf-model' \
  --exclude='openspec/' \
  --exclude='docs/entrega-2/' \
  --exclude='docs/socratic_layer_summary_for_nair*' \
  --exclude='tests/socratic_layer_run*' \
  --exclude='tests/student_history_run*' \
  --exclude='tests/__pycache__/' \
  ./ /tmp/asistente-fisica-space/

# 3. Asegurarse de que .gitattributes tenga el tracking LFS para los binarios.
#    (Una vez configurado en el Space, queda para siempre.)
grep -q '\.bin filter=lfs' /tmp/asistente-fisica-space/.gitattributes || cat >> /tmp/asistente-fisica-space/.gitattributes <<'EOF'
*.bin filter=lfs diff=lfs merge=lfs -text
*.sqlite3 filter=lfs diff=lfs merge=lfs -text
*.pickle filter=lfs diff=lfs merge=lfs -text
EOF

# 4. Forzar que los binarios del bake pasen por el filtro LFS.
#    Sin esto, los blobs quedan como git regular y el push falla con
#    "Your push was rejected because it contains binary files".
cd /tmp/asistente-fisica-space
git rm --cached -r rag/index/chroma/ 2>/dev/null
git add -A

# 5. Commit + push (HF auto-rebuilds).
git -c user.email="fabianalvarez7@users.noreply.huggingface.co" \
    -c user.name="Fabián Álvarez" \
    commit -m "redeploy: <descripción corta del cambio>"
git push origin main
```

Después del push, monitorear el build en https://huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr (la UI muestra el estado: `RUNNING_BUILDING` → `RUNNING`). El primer rebuild con cambios en el bake tarda 1-2 min; si cambia `requirements.txt` o el `Dockerfile`, 5-10 min.

## Pushing binary files (xet storage)

HF reemplazó Git LFS por **xet storage** en 2025. Para pushear binarios (el bake de ChromaDB es el caso nuestro), hay que:

1. Instalar `git-xet` (macOS): `brew install git-xet && git xet install`
2. Tener `git-lfs` instalado (es prerequisito de xet): `brew install git-lfs`
3. Inicializar LFS en el repo del Space: `git lfs install` (solo la primera vez)
4. Configurar el tracking en `.gitattributes`:
   ```
   *.bin filter=lfs diff=lfs merge=lfs -text
   *.sqlite3 filter=lfs diff=lfs merge=lfs -text
   *.pickle filter=lfs diff=lfs merge=lfs -text
   ```
5. **Crítico**: después de añadir `.gitattributes`, los archivos binarios ya commiteados como blobs regulares NO se migran automáticamente. Hay que forzar la reconversión con `git rm --cached -r rag/index/chroma/ && git add -A` antes del commit.

Si te equivocás y el push falla con `Your push was rejected because it contains binary files. Please use https://huggingface.co/docs/hub/xet to store binary files.` — el fix es siempre el paso 5: forzar el re-add con el filtro LFS/xet ya configurado.

## Re-bakear el corpus

Cuando cambie el corpus (PDFs o parámetros de chunking), regenerar el índice desde cero:

```bash
# 1. Re-indexar los 5 PDFs canónicos (tarda ~5-7 h en Mac MPS; es normal).
python scripts/indexar_pdfs.py --reset

# 2. Verificar que marker-pdf recuperó fórmulas en LaTeX antes de seguir.
python scripts/verify_latex.py

# 3. Copiar el índice local al artefacto bakeado que se commitea.
rm -rf rag/index/chroma && cp -r data/chroma rag/index/chroma/

# 4. Commitear y subir al source (GitHub).
git add rag/index/chroma/
git commit -m "chore(data): rebake chroma index (marker-pdf, 5 PDFs)"
git push origin main
```

Después seguir el "Workflow de redeploy" arriba para llevar el nuevo bake al Space.

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

Si un deploy rompe el Space y necesitás volver a una versión que funcionaba, los commits del Space (no los del source) son la fuente de verdad. El último commit conocido como "bueno" se puede restaurar así:

```bash
cd /tmp/asistente-fisica-space
git log --oneline  # encontrar el SHA del commit anterior al problema
git reset --hard <sha-bueno>
git push --force-with-lease origin main
```

El force-push dispara un rebuild. Los datos del Space en runtime (SQLite history) NO se preservan en el rollback — el disco es efímero, se pierden al redeploy.

> Migrado desde Render (que tenía `render.yaml` y disco persistente) a HF Spaces en 2026-06-30. Si volvés a Render en algún momento, el historial tiene `render.yaml` en commits anteriores al switch.

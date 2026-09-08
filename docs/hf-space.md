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
  --exclude='.gitattributes' \
  --exclude='data/' --exclude='.pytest_cache' --exclude='.mypy_cache' \
  --exclude='rag/index/hf-model' \
  --exclude='openspec/' \
  --exclude='docs/entrega-2/' \
  --exclude='docs/socratic_layer_summary_for_nair*' \
  --exclude='tests/socratic_layer_run*' \
  --exclude='tests/student_history_run*' \
  --exclude='tests/__pycache__/' \
  ./ /tmp/asistente-fisica-space/

# 3. Restaurar las reglas LFS en el .gitattributes del Space.
#    ⚠️ El .gitattributes del Space es INTENCIONALMENTE distinto al del source:
#       - Source: vacío (no necesita LFS porque todo lo grande vive en `data/`,
#         que está gitignored).
#       - Space: necesita reglas LFS/xet para que el bake se materialice
#         como binario real al hacer checkout dentro del contenedor.
#    Por eso `--exclude='.gitattributes'` en el rsync: para no pisar las reglas
#    del Space con el archivo vacío del source. Si esto falla, el bake queda
#    como LFS pointer ASCII en el contenedor y ChromaDB crashea al arranque
#    con `chromadb.errors.InternalError: error returned from database:
#    (code: 26) file is not a database`.
grep -q '\.bin filter=lfs' /tmp/asistente-fisica-space/.gitattributes || cat > /tmp/asistente-fisica-space/.gitattributes <<'EOF'
*.bin filter=lfs diff=lfs merge=lfs -text
*.sqlite3 filter=lfs diff=lfs merge=lfs -text
*.pickle filter=lfs diff=lfs merge=lfs -text
EOF

# 4. Forzar que los binarios del bake pasen por el filtro LFS al commitear.
#    Sin esto, los blobs quedan como git regular y el push falla con
#    "Your push was rejected because it contains binary files".
#
#    🐛 Gotcha macOS: Apple Git 2.50.1 NO invoca el filtro LFS automáticamente
#    durante `git add`, ni siquiera con `git lfs install` y `.gitattributes`
#    bien configurados. El filtro SÍ existe (`git lfs clean -- file < file`
#    funciona) pero git no lo invoca en el path de add. Workaround: correr
#    `git lfs clean` manualmente sobre cada binario antes del add para que el
#    working tree contenga pointers y no blobs crudos.
cd /tmp/asistente-fisica-space
git rm --cached -r rag/index/chroma/ 2>/dev/null
for f in $(git status --porcelain | awk '/^.* rag\/index\/chroma/{print $2}'); do
  git lfs clean -- "$f" < "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
git add -A

# 5. Configurar credential helper para el push.
#    🐛 Gotcha HF: desde 2025, HF rechaza autenticación con `user:password@host`
#    en URLs git para operaciones de push (sí funciona para fetch, raro). El push
#    tira "Password authentication in git is no longer supported". Workaround:
#    usar credential helper con el token (el proyecto lo guarda en
#    `HUGGING_FACE_TOKEN` en `.env`, no en `HF_TOKEN`).
TOK=$(grep "^HUGGING_FACE_TOKEN=" .env | head -1 | cut -d= -f2- | tr -d '\n' | tr -d ' ')
printf "https://fabianalvarez7:%s@huggingface.co\n" "$TOK" > /tmp/hf_credentials
chmod 600 /tmp/hf_credentials
git config credential.helper "store --file=/tmp/hf_credentials"
git remote set-url origin "https://huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr"

# 6. Commit + push (HF auto-rebuilds). Usar --force-with-lease si el remote
#    tiene commits divergentes (ej. un commit "test" dejado por una probe API).
git -c user.email="fabianalvarez7@users.noreply.huggingface.co" \
    -c user.name="Fabián Álvarez" \
    commit -m "redeploy: <descripción corta del cambio>"
git push --force-with-lease origin main
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

## Gotchas de LFS / xet en macOS (consolidado)

Tres trampas específicas del entorno de desarrollo (Apple Git + Homebrew xet + HF Spaces) que ya nos costaron tiempo. Si volvés a verlas, mirá primero esta sección.

### 1. Apple Git 2.50.1 no invoca los filtros LFS automáticamente

**Síntoma:** después de `git add -A`, `git ls-files -s <bin>` muestra el hash del contenido binario crudo en lugar del hash del LFS pointer. El commit resultante contiene blobs gigantes, no pointers. El push a HF falla con `Your push was rejected because it contains binary files`.

**Causa:** bug de `git` que viene con CommandLineTools en macOS. El filter driver `filter.lfs.clean` está configurado (`git check-attr` confirma `filter: lfs`) y `git lfs clean -- file` directamente funciona, pero `git add` no invoca el filter.

**Workaround:** correr `git lfs clean` manualmente sobre cada archivo afectado antes del `git add`, para que el working tree contenga pointers y git commitee los pointers sin tener que aplicar el filter él mismo:

```bash
for f in rag/index/chroma/chroma.sqlite3 rag/index/chroma/*/data_level0.bin; do
  git lfs clean -- "$f" < "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
git add -A
```

Verificar con `wc -c rag/index/chroma/chroma.sqlite3` → debería decir ~132 bytes (tamaño típico de un pointer), no 9.5 MB.

### 2. HF rechaza `user:password@host` en URLs para push

**Síntoma:** `git push` falla con `Password authentication in git is no longer supported. You must use a user access token or an SSH key instead`. Pero `git fetch` con el mismo URL anda, y la API REST de HF con el mismo token anda (`/api/whoami-v2` responde 200).

**Causa:** HF endureció la auth para push específicamente (no para fetch). El formato `https://USER:TOKEN@huggingface.co` es interpretado como user:password clásico y rechazado.

**Workaround:** usar credential helper con el token escrito a un archivo separado:

```bash
TOK=$(grep "^HUGGING_FACE_TOKEN=" .env | head -1 | cut -d= -f2- | tr -d '\n')
printf "https://fabianalvarez7:%s@huggingface.co\n" "$TOK" > /tmp/hf_credentials
chmod 600 /tmp/hf_credentials
git config credential.helper "store --file=/tmp/hf_credentials"
git remote set-url origin "https://huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr"
```

Después `git push` lee el helper, encuentra la credencial y la manda como header `Authorization: Bearer ...`, que es lo que HF acepta.

**Variable de entorno:** el proyecto usa `HUGGING_FACE_TOKEN`, no `HF_TOKEN`. Es lo que `huggingface-cli login` escribe por defecto.

### 3. El bake del Space queda como LFS pointer → ChromaDB crashea con `(code: 26)`

**Síntoma:** después de un redeploy exitoso, el Space pasa de `RUNNING` a `RUNTIME_ERROR` con traceback Python:

```
File "/app/rag/retrievers/vector_store.py", line 41, in _get_client
    self._client = PersistentClient(...)
chromadb.errors.InternalError: error returned from database: (code: 26) file is not a database
```

**Causa:** el rsync desde el source sobreescribió el `.gitattributes` del Space. El source tiene `.gitattributes` vacío (no necesita LFS — todo lo grande vive en `data/` gitignored). El Space necesita reglas LFS para que el bake (12 MB de SQLite + binarios) se materialice como blob real durante el checkout, no como pointer ASCII. Sin las reglas, el contenedor arranca con `chroma.sqlite3` como texto de 132 bytes, y ChromaDB tira `SQLITE_NOTADB` al abrirlo.

**Workaround:**
- El rsync ya tiene `--exclude='.gitattributes'` (ver paso 2 del workflow arriba), así que el archivo del Space sobrevive.
- Después del rsync, el script fuerza las reglas LFS al `.gitattributes` del Space (paso 3).
- Verificar el deploy: `curl -s https://huggingface.co/api/spaces/<owner>/<name>/runtime` devuelve `{"stage":"RUNNING",...}`. Si devuelve `RUNTIME_ERROR` con un traceback, ver gotcha #3.

### Bonus: clone inicial del Space con skip-smudge

`git clone` del Space puede fallar con `batch request: missing protocol: "<unknown>"` al hacer smudge de los LFS pointers, incluso con `git-xet` instalado. Workaround:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://fabianalvarez7:${HF_TOKEN}@huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr /tmp/asistente-fisica-space
```

El repo queda clonado con pointers ASCII en lugar de los blobs reales. Para el workflow de redeploy esto está bien (los blobs reales vuelven a aparecer cuando se hace rsync desde el source). Si alguna vez necesitás los blobs reales sin rsync, después del clone podés usar `huggingface-cli download` con `--repo-type=space` y `--include='rag/index/chroma/*'`.

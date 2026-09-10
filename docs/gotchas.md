# Gotchas — Problemas conocidos y workarounds

> Lista viva de problemas que aparecieron durante el desarrollo. Cada gotcha tiene: qué pasa, por qué, y qué hacer.

## Setup e instalación

### Hugging Face sin token puede dar rate limits

**Qué pasa**: warning `Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.`

**Por qué**: por default, las descargas a HuggingFace son anónimas. Funciona, pero son más lentas y pueden dar rate limit en picos.

**Workaround**: pedir un token gratis en https://huggingface.co/settings/tokens y setear `HF_TOKEN=...` en `.env`. No es bloqueante.

### Versiones modernas: API distinta a tutoriales viejos

**Qué pasa**: tutoriales y Stack Overflow de 2023-2024 muestran APIs de `langchain 0.x` que ya no existen en `langchain 1.x` (resolvió a 1.3.11). Mismo con `chromadb 0.x` → 1.5.9 y `sentence-transformers 3.x` → 5.6.0.

**Por qué**: las versiones instaladas son las últimas compatibles con los floors de `requirements.txt`. La API cambió.

**Workaround**: leer la doc oficial actual cuando una API no matchea con el tutorial. Los símbolos están en:
- `langchain_text_splitters.RecursiveCharacterTextSplitter` (paquete separado)
- `chromadb.PersistentClient(path=...)` (reemplaza al viejo `Client`)
- `sentence_transformers.SentenceTransformer(name, device=...)`

## pymupdf4llm (PDF loader)

> **Decisión vigente** desde septiembre 2026. Ver ADR 0001 para la historia completa (2 reversiones desde marker-pdf).

### Pierde fórmulas renderizadas como imágenes

**Qué pasa**: cuando una fórmula está embebida en el PDF como imagen (no como LaTeX escrito en el texto), `pymupdf4llm` no la recupera — el texto alrededor se preserva pero la fórmula se pierde (puede quedar como placeholder vacío o simplemente ausente).

**Por qué**: `pymupdf4llm` extrae texto + estructura Markdown; no hace OCR de imágenes.

**Workaround**: `data/markdown/formulas.md` complementa el catálogo de fórmulas del curso. Está indexado y se inyecta en el retrieval, así que queries del estilo "¿cuál es la fórmula de X?" pueden responder desde ahí aunque el PDF original tenga la fórmula como imagen. Si en el futuro se necesita OCR de fórmulas-imagen, evaluar **Mathpix API** (1000 páginas/mes gratis).

### PDFs escaneados puros: texto vacío

**Qué pasa**: en PDFs que son 100% imágenes (escaneos de pizarra, fotos de ejercicios a mano), `pymupdf4llm` devuelve texto vacío o casi vacío — no hace OCR.

**Por qué**: igual que arriba — sin OCR.

**Workaround**: NO indexar este tipo de PDFs. Pedirle a Nair versiones con texto seleccionable (Word, LaTeX, PDF de libro digital). El cuadernillo sí funciona bien porque tiene texto seleccionable limpio.

### Velocidad: segundos por PDF

**Qué pasa**: `pymupdf4llm` procesa un PDF de ~60 páginas en ~10-20 segundos (load + split + embed + store), comparado con las ~12+ horas que tardaría marker-pdf en el mismo PDF.

**Por qué**: no carga modelos pesados, es un wrapper sobre PyMuPDF que ya viene con la lib.

**Workaround**: ninguno necesario. La indexación cabe en un loop interactivo.

## ChromaDB

### Cambiar `CHROMA_PERSIST_DIR` invalida la colección

**Qué pasa**: si cambiás el path de persistencia, la colección anterior queda "huérfana" en el path viejo y la nueva está vacía.

**Por qué**: ChromaDB identifica la colección por path. No hay migración automática.

**Workaround**: si necesitás cambiar el path, primero `python scripts/indexar_pdfs.py --reset` después de cambiar `.env`.

## History layer (Turso / SQLite)

### La conexión cacheada puede quedar stale y matar todos los endpoints

**Qué pasa**: de repente, `GET /history` y `POST /chat` empiezan a devolver 503 (`"No se pudo guardar la conversación. Reintentá en un momento."` en prod, `"DB error: OperationalError(...)"` en dev). Los assets estáticos cargan bien, el contenedor está vivo, pero **toda la capa de DB falla** hasta que se reinicia el contenedor.

**Por qué**: `rag/history.py` cachea la conexión (Turso o SQLite) a nivel de módulo (`_connection = None`). Si esa conexión muere — TTL de Turso, blip de red, sleep/wake del Space, o un `kill -9` interno del driver — el módulo sigue devolviendo el handle roto porque `_connection is not None`, y cada llamada subsiguiente tira un error de conexión.

**Workaround**: el decorador `_reconnect_on_failure` (en `rag/history.py`) envuelve cada función pública del módulo. Si la primera llamada tira un error de conexión, descarta la conexión cacheada y reintenta la función una vez — `_get_connection` ve `_connection is None` y arma una conexión nueva. Si el reintento también falla, la excepción se propaga como siempre.

**Qué errores atrapa**: el decorador mira la constante `_LIBSQL_ERRORS` (definida arriba en el módulo) más `sqlite3.OperationalError` y `sqlite3.DatabaseError`. La constante se popula en el import del módulo con `libsql_experimental.Error` si el driver está instalado, y queda vacía en dev local. Esto es importante porque **`libsql_experimental.Error` NO está en la jerarquía de `sqlite3`** — su MRO es `['Error', 'Exception', 'BaseException', 'object']`. Si te equivocás y dejás solo las excepciones de `sqlite3`, el reconnect **nunca se dispara** en producción y cada sleep/wake del Space te tira 503 hasta el próximo deploy.

**Si pasa otra vez con un tipo de excepción distinto**: probablemente `libsql_experimental` haya agregado un nuevo tipo de error (ej. `ConnectionError`). Sumalo a `_LIBSQL_ERRORS` arriba, **no** lo metas directo en el `except (...)` del decorador — mantenerlo data-driven hace que sea imposible olvidar el camino del import. Antes de tocar nada, mirá los logs del Space (HF Spaces → tab Logs) — la excepción cruda está ahí, solo que el endpoint la enmascara con `DB_ERROR_MESSAGE` cuando `PRODUCTION=true`.

### `GROQ_API_KEY` rotada pasa el boot check pero rompe el chat silenciosamente

**Qué pasa**: el chat devuelve `event: error\ndata: Ocurrió un error, intentá de nuevo\n\n` (el `_FALLBACK_ERROR` de `chain.py`) y el error queda enmascarado. Los logs del Space muestran 200 OK en `/chat` sin traceback porque la excepción se atrapa en el `except Exception` de `chain.py:180` antes de loguearse. Lo único que se ve es: la conexión a Turso anda, el user message se guarda, el assistant message se guarda con el texto del fallback.

**Por qué**: el boot check en `app/main.py:57` valida con `if not os.getenv("GROQ_API_KEY")` — eso solo detecta que la variable **no esté vacía**. Una key inválida o rotada sigue siendo un string no vacío, pasa el check, y recién falla en la llamada real a la API de Groq con `401 invalid_api_key`. La excepción se loguea solo en la rama dev de `chain.py:186` (cuando `PRODUCTION` no es truthy).

**Workaround / diagnóstico**:
1. **Borrar o poner en `0` el Space Secret `PRODUCTION` momentáneamente**. La rama dev de `chain.py:186` mete la excepción real en el SSE: `event: error\ndata: Error code: 401 - ...`. Con `curl -N` al `/chat` se ve directo. **No olvidar restaurar `PRODUCTION=1` después.**
2. Cuando se rota la API key de Groq (o de cualquier proveedor), hay que actualizar el Space Secret `GROQ_API_KEY` en HF Spaces. Los `.env` locales y los Space Secrets son **fuentes independientes** — renovarla en uno no actualiza al otro.
3. Si querés que el boot check también detecte keys inválidas (no solo vacías), se puede hacer un ping tipo `client.models.list()` al startup. Tradeoff: agrega latencia de boot y depende de que el endpoint `/models` exista. Por ahora el workaround manual es más simple.

**Cómo NO nos morde otra vez**: cuando se renueve la `GROQ_API_KEY` en `console.groq.com`, recordar actualizar **dos** lugares: (1) tu `.env` local, (2) el Space Secret `GROQ_API_KEY` en HF. El test rápido post-deploy es un `curl -N https://<space>.hf.space/chat` con cualquier query — si devuelve `_FALLBACK_ERROR`, la key está mal.

## Splitter (RecursiveCharacterTextSplitter)

### Puede cortar fórmulas LaTeX por la mitad

**Qué pasa**: si una fórmula display (`$$...$$`) es más larga que `chunk_size` (1000 chars por default), el splitter la puede partir a la mitad, dejando chunks con LaTeX roto.

**Por qué**: el splitter default no conoce la sintaxis LaTeX. Solo parte por separadores genéricos (`\n\n`, `\n`, ` `, ``).

**Workaround**: para el cuadernillo, las fórmulas son cortas y no se cortan. Si en el futuro hay fórmulas largas, evaluar:
- Aumentar `chunk_size` a 2000
- Usar `MarkdownTextSplitter` (en langchain) que respeta bloques
- Agregar `$$` a la lista de separadores

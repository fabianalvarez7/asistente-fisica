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

### La conexión de historial puede quedar stale o no responder

**Qué pasa ahora**: si una operación de Turso o SQLite falla dos veces, el chat la saltea en vez de devolver 503. Cada lectura o escritura degrada de forma independiente: `POST /chat` usa el historial que logra leer, conserva las escrituras que sí completan y sigue generando; solo usa historial vacío si falla esa lectura. Una escritura fallida no se persiste ni recibe id. Si falla alguna operación de `GET /history`, ese endpoint responde `{"messages": []}` aunque operaciones anteriores puedan haber completado. No existe backfill automático.

**Por qué**: `rag/history.py` cachea la conexión a nivel de módulo. `_reconnect_on_failure` es ahora un catch-all sobre `Exception` con una whitelist explícita de defectos de programación que se re-eleva sin envolver: `TypeError`, `ValueError`, `AttributeError`, `NameError`, `KeyError`, `IndexError`, `AssertionError`, `sqlite3.ProgrammingError` y `sqlite3.IntegrityError`. Para `sqlite3.OperationalError` se mira el código numérico: SQLITE_BUSY/LOCKED/READONLY/IOERR/FULL/CANTOPEN/PROTOCOL se tratan como availability, SQLITE_ERROR/SQLITE_SCHEMA se tratan como defecto. Cualquier otro `Exception` — `libsql.Error`, `OSError` y sus subclases (`ConnectionError`, `TimeoutError`, `socket.gaierror`), y cualquier tipo nuevo que aparezca en una versión futura de libsql — degrada el historial en vez de romper el endpoint. `BaseException` (KeyboardInterrupt, SystemExit, asyncio.CancelledError) sigue propagando sin ser capturado.

**Señal segura**: cada degradación escribe un log nivel `ERROR` con `operation`, `wrapper_type` y `root_cause_type`. Nunca registra texto de la excepción, nombres, preguntas, respuestas, SQL, URLs, tokens ni secretos. Para el prototipo pre-demo, revisar manualmente los logs del Space antes y después del ensayo. Alertas automáticas/Sentry quedan como seguimiento post-demo.

**Runbook pre-demo**:
1. Despertar el Space con anticipación, abrir un chat, enviar una pregunta, recargar y confirmar que el turno aparece en el historial. Revisar que no haya logs `History unavailable`.
2. Si Turso falla de forma sostenida, quitar temporalmente **ambas** variables de Turso y reiniciar el Space para activar SQLite local de manera explícita. Nunca hacer fallback automático con una identidad Turso activa.
3. Asumir el tradeoff: ese historial local es efímero, puede perderse al dormir/reiniciar el Space y no se sincroniza de vuelta a Turso. Restaurar ambas variables y reiniciar después de la contingencia.

**Riesgo aceptado**: el driver instalado no ofrece timeout ni cancelación. El modo degradado actúa cuando una llamada devuelve error, pero no puede rescatar una llamada nativa que queda bloqueada. Para la demo, la mitigación es el ensayo previo, inspección manual y la contingencia SQLite explícita; mover llamadas a threads con timeout no cancela el write y puede empeorar la concurrencia.

### `GROQ_API_KEY` rotada pasa el boot check pero rompe el chat silenciosamente

**Qué pasa**: el chat devuelve `event: error\ndata: Ocurrió un error, intentá de nuevo\n\n` (el `_FALLBACK_ERROR` de `chain.py`) y el error queda enmascarado. Los logs del Space muestran 200 OK en `/chat` sin traceback porque la excepción se atrapa en el `except Exception` de `chain.py:180` antes de loguearse. Lo único que se ve es: la conexión a Turso anda, el user message se guarda, el assistant message se guarda con el texto del fallback.

**Por qué**: el boot check en `app/main.py:57` valida con `if not os.getenv("GROQ_API_KEY")` — eso solo detecta que la variable **no esté vacía**. Una key inválida o rotada sigue siendo un string no vacío, pasa el check, y recién falla en la llamada real a la API de Groq con `401 invalid_api_key`. La excepción se loguea solo en la rama dev de `chain.py:186` (cuando `PRODUCTION` no es truthy).

**Workaround / diagnóstico**:
1. **Borrar o poner en `0` el Space Secret `PRODUCTION` momentáneamente**. La rama dev de `chain.py:186` mete la excepción real en el SSE: `event: error\ndata: Error code: 401 - ...`. Con `curl -N` al `/chat` se ve directo. **No olvidar restaurar `PRODUCTION=1` después.**
2. Cuando se rota la API key de Groq (o de cualquier proveedor), hay que actualizar el Space Secret `GROQ_API_KEY` en HF Spaces. Los `.env` locales y los Space Secrets son **fuentes independientes** — renovarla en uno no actualiza al otro.
3. Si querés que el boot check también detecte keys inválidas (no solo vacías), se puede hacer un ping tipo `client.models.list()` al startup. Tradeoff: agrega latencia de boot y depende de que el endpoint `/models` exista. Por ahora el workaround manual es más simple.

**Cómo NO nos morde otra vez**: cuando se renueve la `GROQ_API_KEY` en `console.groq.com`, recordar actualizar **dos** lugares: (1) tu `.env` local, (2) el Space Secret `GROQ_API_KEY` en HF. El test rápido post-deploy es un `curl -N https://<space>.hf.space/chat` con cualquier query — si devuelve `_FALLBACK_ERROR`, la key está mal.

### Fallos de transporte de libsql (`OSError`) escapan al endpoint si no se atrapan explícitamente

**Qué pasa (antes del fix `d8e395f` / `65636b3`)**: después de varias horas de uptime con poco tráfico a Turso, el Space dejaba de responder con HTTP 500 en `/history` y `/chat`. En el frontend eso se veía como "No se pudo cargar el historial" en la carga inicial y "Ocurrió un error, intentá de nuevo" al mandar una pregunta — los mismos síntomas que un Turso caído pero **sin** la degradación esperada (historial vacío + chat funcionando). El único workaround era `Restart Space` desde la UI de HF.

**Por qué**: `libsql-experimental 0.0.55` habla con Turso por sockets. Cuando la red se cae (DNS inaccesible, connection refused por Turso pausado, TLS error, read timeout), la excepción que sube es un `OSError` crudo — **no** un `libsql.Error`. La catch list original de `_reconnect_on_failure` solo cubría `sqlite3.OperationalError` y `libsql.Error`, así que el `OSError` la atravesaba sin ser reconectado ni envuelto como `HistoryUnavailableError`. En `app/main.py` los endpoints solo capturan `HistoryUnavailableError`, así que cualquier otra excepción burbujea como 500. La raíz: confundir "driver error" (lo que captura libsql) con "transport error" (lo que captura el socket subyacente).

**Por qué ahora sí está cubierto**: a partir de `e0c679d` / Space `65636b3`, `_reconnect_on_failure` dejó de mantener una catch list estrecha y pasó a un catch-all sobre `Exception` con una whitelist explícita de defectos de programación que SÍ deben propagar como 500 (`TypeError`, `ValueError`, `AttributeError`, `NameError`, `KeyError`, `IndexError`, `AssertionError`, `sqlite3.ProgrammingError`, `sqlite3.IntegrityError`, y `sqlite3.OperationalError` con códigos no-disponibles como `SQLITE_ERROR`/`SQLITE_SCHEMA`). Cualquier otro tipo de excepción — `OSError`, `libsql.Error`, `RuntimeError`, o algo exótico que aparezca en una versión futura — degrada el historial en vez de romper el endpoint. Fin del whack-a-mole.

**Cómo NO nos morde otra vez**:
1. `_reconnect_on_failure` ya no distingue tipos para clasificar — solo distingue "defecto de programación conocido" vs "lo demás". Tests de regresión en `tests/test_chat_sse_message_ids.py::HistoryPersistenceBoundaryTests`:
   - `test_repeated_oserror_is_translated_with_cause`, `test_oserror_on_first_attempt_recovers_on_retry`, `test_oserror_subclasses_are_also_translated` (cubre `ConnectionError`, `TimeoutError` y `OSError` base).
   - `test_unknown_exception_type_is_treated_as_availability`: confirma que cualquier `Exception` no whitelisteada degrada.
   - `test_programming_defects_propagate_unchanged`: sweep por toda la whitelist — cada defecto propaga sin retry, sin reset, sin wrap.
   - `test_programming_defect_on_retry_propagates`: si la primera llamada es availability pero la segunda encuentra un bug, el bug surface a través del wrapping.
2. **No expandir la whitelist sin justificación**. Cada tipo que se agrega enmascara un bug real. La regla: si una excepción subió y querés que degrade, dejala pasar por el catch-all (no la agregues a `_PROGRAMMING_DEFECTS`).
3. El test rápido post-deploy para verificar la degradación esperada (no 500): `curl -i https://<space>.hf.space/history?student_name=foo` debe devolver **200** con `{"messages": []}` aunque Turso esté caído. Si devuelve 500, el catch-all se rompió y hay que mirar `_is_programming_defect` (probablemente se agregó algo a la whitelist por error).
4. Si el comportamiento deja de degradar (chat sigue intentando escribir/ leer y se traba), revisar `libsql-experimental` — quizás una versión nueva introdujo una `BaseException` subclass o un comportamiento que rompe el contrato `except Exception`.

## Splitter (RecursiveCharacterTextSplitter)

### Puede cortar fórmulas LaTeX por la mitad

**Qué pasa**: si una fórmula display (`$$...$$`) es más larga que `chunk_size` (1000 chars por default), el splitter la puede partir a la mitad, dejando chunks con LaTeX roto.

**Por qué**: el splitter default no conoce la sintaxis LaTeX. Solo parte por separadores genéricos (`\n\n`, `\n`, ` `, ``).

**Workaround**: para el cuadernillo, las fórmulas son cortas y no se cortan. Si en el futuro hay fórmulas largas, evaluar:
- Aumentar `chunk_size` a 2000
- Usar `MarkdownTextSplitter` (en langchain) que respeta bloques
- Agregar `$$` a la lista de separadores

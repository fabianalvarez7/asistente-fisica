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

## marker-pdf (PDF loader)

### MPS parcial: TableRecEncoderDecoderModel no soporta MPS

**Qué pasa**: warning `surya: TableRecEncoderDecoderModel is not compatible with mps backend. Defaulting to cpu instead`. marker tarda ~2 min/página en Mac con MPS (no ~10s como sería en H100).

**Por qué**: ese modelo específico no fue portado a MPS. El resto del pipeline sí corre en MPS.

**Workaround**: ninguno conocido. La única forma de acelerar es GPU con CUDA (Mac con eGPU, o Linux con NVIDIA). Para el prototipo, aceptar los 2 min/pág y correr la indexación de noche.

### marker NO maneja bien PDFs escaneados puros

**Qué pasa**: en PDFs que son 100% imágenes (escaneos de pizarra, fotos de ejercicios a mano), marker tarda mucho más (~24 min/10 pgs) y la calidad del OCR es pésima — alucina símbolos y repite texto.

**Por qué**: surya-OCR está entrenado principalmente para texto impreso y tablas, no para escritura a mano o figuras complejas.

**Workaround**: NO indexar este tipo de PDFs. Pedirle a Nair versiones con texto seleccionable (Word, LaTeX, PDF de libro digital). El cuadernillo sí funciona bien.

### Cada llamada a marker en proceso nuevo paga el costo completo

**Qué pasa**: si corrés `python script.py` dos veces, marker tarda 10 min en cada proceso (carga modelos + procesa PDFs), aunque los modelos ya estén en disco.

**Por qué**: el converter de marker NO se puede serializar a disco. Vive solo en memoria del proceso.

**Workaround**: agrupar todas las operaciones en un solo proceso. El `scripts/indexar_pdfs.py` ya hace esto. Si querés evitar pagar el costo cada vez, NO se puede — el costo de marker es one-shot por invocación.

### Modelos cacheados en `~/Library/Caches/datalab/models/` (macOS)

**Qué pasa**: marker descarga ~3GB de modelos la primera vez. En runs siguientes, los modelos se leen del cache.

**Por qué**: el cache es por usuario. Si cambias de usuario o borras `~/Library/Caches/`, marker vuelve a descargar.

**Workaround**: si reinstalás macOS o cambiás de Mac, hay que volver a descargar. Es una sola vez.

### Fórmulas inline mal interpretadas

**Qué pasa**: algunas fórmulas inline se interpretan con heurísticas incorrectas. Ejemplo: en el cuadernillo, `x = A/U` (división) se convirtió en `$x = {A \choose U}$` (binomial, notación incorrecta).

**Por qué**: el modelo de fórmulas inline usa heurísticas que a veces confunden notación.

**Workaround**: las fórmulas en display (`$$...$$`) salen bien. Las inline, revisar manualmente. Para el caso de uso del asistente Socrático, es acceptable — el LLM puede reformular.

### Variables perdidas en OCR

**Qué pasa**: a veces variables se pierden o malinterpretan. Ejemplo del cuadernillo: "El X' es en nuestro ejemplo 14,5 cm" se convirtió en "El ' es en nuestro ejemplo 14, 5 , el valor verdadero...".

**Por qué**: OCR/heurística de marker no es perfecta.

**Workaround**: aceptar el ruido. Para RAG, el chunk sigue siendo útil (contiene las palabras clave). Para publicación, habría que revisar a mano.

## ChromaDB

### Cambiar `CHROMA_PERSIST_DIR` invalida la colección

**Qué pasa**: si cambiás el path de persistencia, la colección anterior queda "huérfana" en el path viejo y la nueva está vacía.

**Por qué**: ChromaDB identifica la colección por path. No hay migración automática.

**Workaround**: si necesitás cambiar el path, primero `python scripts/indexar_pdfs.py --reset` después de cambiar `.env`.

### Conflictos con `sentence-transformers` por versiones de transformers

**Qué pasa**: marker-pdf requiere `transformers < 5` (downgradea de 5.12 a 4.57) y `huggingface-hub < 1` (downgradea de 1.20 a 0.36). sentence-transformers usa transformers también.

**Por qué**: marker-pdf depende de surya-ocr 0.17, que no es compatible con transformers 5.x.

**Workaround**: por ahora todo funciona. Si en el futuro hay incompatibilidad, ver si marker-pdf sacó nueva versión compatible con transformers 5.x.

## Splitter (RecursiveCharacterTextSplitter)

### Puede cortar fórmulas LaTeX por la mitad

**Qué pasa**: si una fórmula display (`$$...$$`) es más larga que `chunk_size` (1000 chars por default), el splitter la puede partir a la mitad, dejando chunks con LaTeX roto.

**Por qué**: el splitter default no conoce la sintaxis LaTeX. Solo parte por separadores genéricos (`\n\n`, `\n`, ` `, ``).

**Workaround**: para el cuadernillo, las fórmulas son cortas y no se cortan. Si en el futuro hay fórmulas largas, evaluar:
- Aumentar `chunk_size` a 2000
- Usar `MarkdownTextSplitter` (en langchain) que respeta bloques
- Agregar `$$` a la lista de separadores

## Decisión: NO migrar a GPU dedicada

**Por qué**: la inversión (eGPU + setup) no se amortiza para un corpus de <100 páginas que se indexa una vez. El plan es aceptar la indexación lenta en Mac con MPS y correrla de noche cuando llegue material nuevo.

**Si cambia**: con 50+ PDFs limpios, el costo de marker empieza a ser prohibitivo en Mac. Ahí evaluar Render con GPU o un servicio de indexación dedicado.

# ADR 0001: Cambio de PDF loader de pymupdf4llm a marker-pdf

- **Estado**: Aceptado
- **Fecha**: 2026-06-24
- **Sesión**: bootstrap semana 1-2

## Contexto

Inicialmente adoptamos `pymupdf4llm` como loader de PDFs (mencionado en AGENTS.md sección 4) por ser liviano y rápido. Al probarlo con los 8 PDFs del corpus inicial descubrimos que:

- Los PDFs son una mezcla de texto seleccionable, escaneos, fotos de ejercicios hechos a mano y partes de libros. Solo el cuadernillo (5 páginas) tiene texto limpio.
- `pymupdf4llm` descarta las imágenes, lo que incluye las **fórmulas embebidas como imágenes** — algo crítico para un asistente de Física donde la pregunta típica del estudiante es "¿cuál es la fórmula de...?".

En el cuadernillo, página 3 (la que tiene 6 fórmulas sobre error relativo y precisión), pymupdf4llm devolvía 6 placeholders `**==> picture [N x M] intentionally omitted <==**`. El texto alrededor se preservaba, pero las fórmulas concretas se perdían.

Evaluamos `marker-pdf` (datalab) y `Mathpix` (API cloud) como alternativas.

## Decisión

Migramos el loader a `marker-pdf`.

## Benchmarks consultados (oficiales de marker-pdf, H100)

| Método | Tiempo/pág | Score heurístico | Score LLM |
|---|---|---|---|
| **marker** | 2.84s | **95.67** | 4.24 |
| mathpix | 6.36s | 86.43 | 4.16 |
| docling | 3.70s | 86.71 | 3.70 |
| llamaparse | 23.35s | 84.24 | 3.98 |

Por tipo de documento (heuristic score):

| Tipo | marker | mathpix |
|---|---|---|
| **Book page** (nuestro caso) | **97.18** | 93.89 |
| Scientific paper | 96.67 | 91.23 |
| Engineering document | 93.92 | 80.33 |

Marker gana en todo, **y por más diferencia cuanto más complejo es el documento**.

## Consecuencias

### Positivas

- **Fórmulas rescatadas como LaTeX**. En el cuadernillo pág 3, marker recuperó las 5 fórmulas de error relativo/precisión como `$$Er_X = \frac{\Delta X}{X'} \tag{3}$$`, `$$Er_{\%} = 100 \cdot \frac{\Delta X}{X'} \tag{4}$$`, etc. El retrieval matchea consultas como "fórmula de error relativo" con el LaTeX exacto.
- **Corre local** (sin API key, sin costos recurrentes). Alineado con decisión #3 del AGENTS.md (local embeddings, no API).
- **Soporta MPS (Mac)**, CUDA y CPU.
- **Open source**: GPL-3.0 (código) + OpenRAIL-M (modelos). Gratis para nuestro caso (startup <$2M funding).
- **No requiere Mathpix** ni dependencia de API externa — funciona offline después de la primera descarga de modelos.

### Negativas (aceptadas)

- **Tiempo de indexación inicial**: ~2 min/página en Mac con MPS (parcial, parte del pipeline cae a CPU). Para los 8 PDFs (151 páginas) son ~5 horas. Pero se hace una sola vez por corpus, o cuando cambia el material.
- **Calidad de OCR no es perfecta**: hay errores de variables perdidas (ej. "El ' es" en vez de "El X' es") y de heurística de fórmulas inline (ej. `$x = {A \choose U}$` en vez de `$x = A/U$`). Aceptable para RAG, no para publicación académica.
- **Descarga inicial de modelos ~3GB**. Se cachea en `~/Library/Caches/datalab/models/`. Es una sola vez.
- **MPS parcial**: el modelo `TableRecEncoderDecoderModel` no soporta MPS y cae a CPU. Aceptable pero explica la lentitud vs. H100.

## PDFs escaneados: descartados por ahora

Para los PDFs escaneados puros del corpus inicial (`04-clase-09-04-2025.pdf`, `05-cinematica-2d.pdf`, `06-dinamica.pdf`, `07-movimiento-circular.pdf`, `08-torque.pdf` parcial), marker tarda ~2.5 min/página y la calidad de OCR es **horrible** (alucinaciones como `\vee_1, \vee_2, ...` repetido 200 veces cuando "lee" una tabla compleja).

**Decisión**: no indexamos estos PDFs hasta que Nair provea versiones con texto seleccionable (Word, LaTeX, o PDFs de libros digitales). Los 8 PDFs actuales no entran al corpus inicial; el cuadernillo es el único que se indexa.

## Alternativas descartadas

- **Mathpix**: descartado por requerir API key + dependencia externa + costos después del free tier (1000 páginas/mes). El free tier alcanza para el corpus actual, pero el proyecto escala mejor sin API.
- **Docling**: menor accuracy que marker en benchmarks.
- **Llamaparse**: peor accuracy y más caro (cloud).
- **Loader híbrido (pymupdf4llm para texto + marker solo para PDFs con fórmulas)**: descartado por over-engineering para el prototipo. Si en el futuro indexar muchos PDFs de texto puro se vuelve un cuello de botella, lo evaluamos.

## Notas de implementación

- API: `load_pdf(path) -> list[Document]` con un único Document por PDF (no por página). El chunker parte el markdown después.
- Metadata: `{'source': str(path)}`. No incluye `page` por simplicidad — si hace falta, agregar `paginate_output=True` y partir por el separador.
- Modelos cacheados en singleton (`_CONVERTER`) — no se recargan entre llamadas.
- `disable_image_extraction=True` para no llenar `data/` de imágenes que no usamos.

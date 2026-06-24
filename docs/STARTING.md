# Cómo Empezar — Semana 1-2

> Esta es tu guía para arrancar mañana. El `AGENTS.md` es la constitución del proyecto; este documento es tu mapa de los primeros pasos. Releelo cada vez que vuelvas a esto después de un finde.

## Mentalidad (leé esto antes de tocar una línea)

Las primeras dos semanas **NO son para hacer el chat**. Son para construir la base del RAG y validar que recupera información útil de los PDFs. Si esto no anda bien, nada de lo que viene después importa.

Lo que vas a lograr al final de la semana 2:

- Los PDFs indexados en ChromaDB.
- Un script de Python en la terminal que toma una pregunta y devuelve los chunks más relevantes.
- La confirmación (con pruebas tuyas) de que la recuperación tiene sentido pedagógico.

**Esto es aprendizaje de ingeniería de IA, no solo cumplimiento de tareas.** Las decisiones que tomes acá (chunking, embeddings, prompts de pre-procesamiento) van a condicionar todo lo demás. Andate despacio, entendé lo que hacés.

## Checklist de la semana 1-2

### Día 1: Setup del repo

- [ ] Crear la estructura de carpetas según sección 5 del `AGENTS.md` (`app/`, `dashboard/`, `rag/`, `scripts/`, `data/`, `tests/`, `docs/`).
- [ ] `git init`, primer commit con el `AGENTS.md` y este documento.
- [ ] Crear `requirements.txt` con dependencias básicas (ver más abajo).
- [ ] Crear `.gitignore` con: `.venv/`, `data/`, `.env`, `__pycache__/`, `*.pyc`.
- [ ] Crear `.env.example` con `GROQ_API_KEY=` y `EMBEDDINGS_DEVICE=auto`.

### Días 2-3: Pipeline PDF → Markdown

- [ ] Copiar los 8 PDFs de Nair a `data/pdfs/` (esta carpeta está gitignored).
- [ ] Instalar `pymupdf4llm` y probar con UN PDF primero.
- [ ] Crear `rag/loaders/__init__.py` y `rag/loaders/pdf_loader.py` que lea PDFs y devuelva Markdown.
- [ ] Probar con los 8 PDFs. **Si las fórmulas se ven mal, evaluar `marker-pdf` o Mathpix** (ver Gotchas abajo).

### Días 4-5: Chunking + Embeddings + ChromaDB

- [ ] Decidir estrategia de chunking. **Empezá con tamaño fijo** (ej: 1000 caracteres con overlap 200). Es lo más simple y vas a poder comparar.
- [ ] Crear `rag/splitters/__init__.py` y `rag/splitters/text_splitter.py`.
- [ ] Instalar `sentence-transformers` y cargar el modelo `intfloat/multilingual-e5-small`. **Confirmá que en tu Mac usa MPS** (debería detectarlo solo, pero verificá).
- [ ] Crear `rag/retrievers/__init__.py` y `rag/retrievers/embeddings.py`.
- [ ] Crear `rag/retrievers/vector_store.py` con ChromaDB persistente en `./data/chroma/`.
- [ ] Probar indexar los 8 PDFs.

### Días 6-7: Script de consulta en terminal

- [ ] Crear `scripts/indexar_pdfs.py` (lee PDFs, los indexa, idempotente — si corrés dos veces no duplica).
- [ ] Crear `scripts/query.py` que toma una pregunta por stdin y devuelve los top-k chunks.
- [ ] Probar con 5-10 preguntas típicas de Física 1. **Validar manualmente que los chunks son relevantes.** Esto es investigación, no check-the-box.

### Días 8-9: Validación + iteración

- [ ] Probar preguntas más complejas (multi-concepto, con fórmulas, con gráficos referenciados).
- [ ] Verificar latencia razonable (< 5 segundos por consulta).
- [ ] Documentar en `docs/` lo que aprendiste: gotchas, cosas que no andan, decisiones de diseño que tomaste. Esto te sirve a vos en 2 meses y a quien venga después.

## Comandos esenciales (copy-paste)

```bash
# Setup inicial (Día 1)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu GROQ_API_KEY (cada dev tiene la suya)

# Verificar que el modelo de embeddings usa MPS en tu Mac
python -c "import torch; print('MPS disponible:', torch.backends.mps.is_available())"

# Indexar todos los PDFs
python scripts/indexar_pdfs.py

# Probar una consulta en terminal
python scripts/query.py "¿Qué es la energía cinética?"
```

## `requirements.txt` sugerido para arrancar

```
# RAG
langchain
langchain-community
chromadb
sentence-transformers
pymupdf4llm

# Utilidades
python-dotenv
tiktoken
```

Irá creciendo a medida que agregues FastAPI, Streamlit, etc. **No metas dependencias que no usás todavía.**

## Gotchas que vas a encontrar (leé esto ANTES de que te traben)

- **MPS en Mac Apple Silicon**: si `sentence-transformers` no usa MPS, revisá que PyTorch tenga soporte MPS. `pip install --upgrade torch` suele alcanzar. Verificá con el comando de arriba.
- **PDFs con imágenes/fórmulas**: si `pymupdf4llm` devuelve markdown sin imágenes ni fórmulas visibles, las fórmulas en imágenes no se indexan. **Ahí evaluás `marker-pdf` o Mathpix** (free tier 1000 páginas/mes). No es el fin del mundo si arranca parcial — el AGENTS.md dice RAG parcial primero.
- **Fórmulas en LaTeX**: `pymupdf4llm` suele preservarlas. Si el retrieval no las encuentra, es tema del chunking, no del loader.
- **Primera indexación lenta**: con 8 PDFs está bien, pero si crece, considerá hacerlo en background.
- **ChromaDB persistente**: si cambiás `CHROMA_PERSIST_DIR`, la colección "se pierde" (archivo huérfano). Cada vez que cambiás el path, reindexá.
- **LangChain como caja de herramientas**: usá solo lo que necesitás (loaders, splitters, retrievers). **NO uses** `RetrievalQA` con prompts built-in, ni `Agents`, ni `Memory` de LangChain. El AGENTS.md sección 7, decisión 9 es dura acá. Escribí la orquestación vos en `rag/chain.py`.

## Recursos para profundizar (buscá solo lo que necesitás en el momento)

- **LangChain — Document Loaders y Text Splitters**: https://python.langchain.com/docs/modules/data_connection/
- **ChromaDB — Getting Started**: https://docs.trychroma.com/getting-started
- **sentence-transformers — Quickstart**: https://www.sbert.net/docs/quickstart.html
- **pymupdf4llm**: https://github.com/pymupdf/RAG

No trates de leer todo de entrada. Buscá el recurso cuando estés trabado en ese paso específico.

## Lo que NO hay que hacer todavía (anti-recordatorios)

- **No armes la web todavía** (eso es semana 3-4). El terminal es suficiente.
- **No toques la capa socrática** (eso es semana 5-6). El RAG primero.
- **No instales Docker** (no entra en el plan, lo charlamos).
- **No uses las abstracciones de alto nivel de LangChain** (Agents, Memory, RetrievalQA con prompts built-in). Decisión 9 del AGENTS.md.
- **No clones repos de RAG hechos**. Decisión 10 del AGENTS.md.
- **No agregues features que Nair no pidió**. Si se te ocurre algo, anotalo en `docs/ideas.md` y lo charlamos.

## Cuando te trabes

Si te pasás **más de 1-2 horas atascado en algo sin avanzar**, volvé a la sesión y charlamos. No te quedes peleando solo. Mejor perder 10 minutos preguntando que perder 3 horas en un callejón sin salida.

Y cuando algo ande (aunque sea parcial), **anotalo en `docs/`**: lo que decidiste, por qué, qué probaste, qué descartaste. Tu vos del futuro te lo va a agradecer.

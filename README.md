# Asistente de Física

> Asistente Socrático de chat para estudiantes de **Física 1** (UNR). El asistente guía con preguntas; nunca resuelve el ejercicio. Las respuestas se generan exclusivamente desde los PDFs de la materia.

## Stack

| Capa | Tech |
|---|---|
| Backend | FastAPI (semana 3-4) |
| RAG | LangChain como toolbox + orquestación propia en `rag/` |
| Vector store | ChromaDB (persistente, local) |
| PDF loader | marker-pdf (con OCR + LaTeX) |
| Embeddings | `intfloat/multilingual-e5-small` (local, MPS/CUDA/CPU) |
| LLM | Groq (API) |
| Persistencia | SQLite (semana 5-6) |
| Frontend chat | HTML + JS plano (semana 3-4) |
| Frontend dashboard | Streamlit (mes 3, opcional) |
| Deploy | Render free tier |

Decisiones de arquitectura y no-negociables del proyecto: ver `AGENTS.md`.

## Prerrequisitos

- **Python 3.11+** (probado con 3.12)
- **macOS** (Apple Silicon) o **Windows** con NVIDIA GPU, o **Linux** (CPU)
- **~3 GB de disco libre** para los modelos de marker-pdf (se cachean en `~/Library/Caches/datalab/models/` en macOS)
- **Una API key de Groq** (gratis) en https://console.groq.com

## Setup

```bash
# 1. Clonar
git clone <repo-url> asistente-fisica
cd asistente-fisica

# 2. Virtualenv
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar secretos
cp .env.example .env
# Editar .env y setear GROQ_API_KEY

# 5. (Una vez) Copiar PDFs a indexar a data/pdfs/
# Los PDFs originales viven en material-fisica/ (gitignored)

# 6. Indexar (tarda ~10 min por PDF de 5 páginas en Mac con MPS)
python scripts/indexar_pdfs.py

# 7. Probar retrieval (próximamente: scripts/query.py en Día 6-7)
```

## Estructura

```
asistente-fisica/
├── app/                 # FastAPI backend (semana 3-4)
├── dashboard/           # Streamlit (mes 3, opcional)
├── rag/                 # Lógica de RAG
│   ├── loaders/         # PDF → Markdown (marker-pdf)
│   ├── splitters/       # Chunking (RecursiveCharacterTextSplitter)
│   ├── retrievers/      # Embeddings + ChromaDB
│   ├── prompts/         # System prompts (mes 2)
│   └── chain.py         # Orquestación RAG (mes 2)
├── scripts/             # CLI: indexar_pdfs.py, query.py
├── data/                # ChromaDB + SQLite (gitignored)
├── tests/
├── docs/
│   ├── STARTING.md      # Playbook semana 1-2
│   ├── STATUS.md        # Estado del proyecto
│   ├── gotchas.md       # Problemas conocidos y workarounds
│   └── adr/             # Architecture Decision Records
└── AGENTS.md            # Constitución del proyecto
```

## Estado actual

Cerramos la **semana 1-2** del roadmap. El pipeline RAG funciona end-to-end sobre el cuadernillo (Teoría de Errores). Ver `docs/STATUS.md` para detalle.

## Documentación

- **`AGENTS.md`** — Constitución del proyecto (leer primero)
- **`docs/STARTING.md`** — Playbook día-por-día de la semana 1-2
- **`docs/STATUS.md`** — Dónde estamos, qué falta
- **`docs/gotchas.md`** — Problemas conocidos y workarounds
- **`docs/adr/`** — Decisiones arquitectónicas con justificación

## Licencia

MIT (a confirmar con Nair/Fabián).

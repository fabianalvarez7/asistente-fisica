# FaradAI - Asistente de Física

> FaradAI es un asistente de chat para estudiantes de **Física 1** de la Facultad de Cs. Bioquímicas y Farmacéuticas de la Universidad Nacional de Rosario. El asistente guía al alumno con preguntas, para transmitir los conceptos teóricos y la resolución de ejercicios, pero nunca responde directamente. Las respuestas se generan exclusivamente desde la bibliografía de la materia, con el catálogo de los ejercicios que se dan durante el cursado, resueltos con el procedimiento determinado por los profesores.

## Stack

| Capa | Tech |
|---|---|
| Backend | Python y FastAPI |
| RAG | LangChain como toolbox + orquestación propia en `rag/` |
| Vector store | ChromaDB (persistente, local) |
| PDF loader | pymupdf4llm |
| Embeddings | `intfloat/multilingual-e5-small` (local, MPS/CUDA/CPU) |
| LLM | Groq (API) |
| Persistencia | SQLite |
| Frontend chat | HTML + JS plano |
| Deploy | Hugging Face Spaces |

## Prerrequisitos

- **Python 3.11+** (probado con 3.12)
- **macOS** (Apple Silicon) o **Windows** con NVIDIA GPU, o **Linux** (CPU)
- **~600 MB de disco libre** para el modelo de embeddings `intfloat/multilingual-e5-small` (ya viene pre-bakeado en `rag/index/hf-model/`, LFS-tracked)
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
├── app/                 # FastAPI backend
├── rag/                 # Lógica de RAG
│   ├── loaders/         # PDF → Markdown (pymupdf4llm)
│   ├── splitters/       # Chunking (RecursiveCharacterTextSplitter)
│   ├── retrievers/      # Embeddings + ChromaDB
│   ├── prompts/         # System prompts
│   └── chain.py         # Orquestación RAG
├── scripts/             # CLI: indexar_pdfs.py, query.py
├── data/                # ChromaDB + SQLite (gitignored)
├── tests/
├── docs/
│   ├── STARTING.md      # Playbook
│   ├── STATUS.md        # Estado del proyecto
│   ├── gotchas.md       # Problemas conocidos y workarounds
│   └── adr/             # Architecture Decision Records
└── AGENTS.md            # Constitución del proyecto
```

## Licencia MIT.

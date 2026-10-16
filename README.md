# FaradAI - Asistente de Física

> FaradAI es un asistente de chat para estudiantes de **Física 1** de la Facultad de Cs. Bioquímicas y Farmacéuticas de la Universidad Nacional de Rosario. El asistente guía al alumno con preguntas, para transmitir los conceptos teóricos y la resolución de ejercicios, pero nunca responde directamente. Las respuestas se generan exclusivamente desde la bibliografía de la materia, con el catálogo de los ejercicios que se dan durante el cursado, resueltos con el procedimiento determinado por los profesores.
>
> Fue desarrollado en el marco de la convocatoria XperienciaUNR a cargo del Laboratorio de Experimentación Tecnológica (LET UNR) del Área de Ciencia, Tecnología e Innovación de la Universidad Nacional de Rosario. El prototipo es implementado por un grupo interdisciplinario formado por:
> - Nair Sarquis, promotora (profesora de física de la FBIOyF de la UNR)
> - Tatiana Gangge, gestora (alumna de Comunicación Social UNR)
> - Fabián Alvarez, desarrollador (alumno de la Tecnicatura en Inteligencia Artificial UNR)
> - Justo Irribarren, diseñador (alumno de Diseño Gráfico UNR)

## Stack

| Capa | Tech |
|---|---|
| Backend | Python y FastAPI |
| RAG | LangChain como toolbox + orquestación propia en `rag/` |
| Vector store | ChromaDB (persistente, local) |
| PDF loader | pymupdf4llm |
| Embeddings | `intfloat/multilingual-e5-small` (local, MPS/CUDA/CPU) |
| LLM | Groq (modelo `openai/gpt-oss-120b`) |
| Persistencia | SQLite (Turso/libSQL en producción) |
| Frontend chat | HTML + CSS + JS plano |
| Frontend dashboard | HTML + CSS + JS plano (Streamlit queda como fallback) |
| Deploy | Hugging Face Spaces Docker (cpu-basic, 16 GB RAM) |

## Prerrequisitos

- **Python 3.11+** (probado con 3.12)
- **macOS** (Apple Silicon) o **Windows** con NVIDIA GPU, o **Linux** (CPU)
- **~600 MB de disco libre** para el modelo de embeddings `intfloat/multilingual-e5-small` (en el Space lo descarga el Dockerfile en build time; en local, se baja la primera vez que corre la app)
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
# En producción (HF Spaces): TURSO_DATABASE_URL y TURSO_AUTH_TOKEN también son obligatorios (Secrets).

# 5. Indexar los PDFs del cuadernillo (los originales viven en material-fisica/, gitignored)
python scripts/indexar_pdfs.py

# 6. Levantar el chat
uvicorn app.main:app --reload
# → http://localhost:8000           chat de teoría
# → http://localhost:8000/exercises catálogo de ejercicios tutor
# → http://localhost:8000/dashboard dashboard público para profesoras

# 7. (Solo para deploy HF Spaces) Re-bakear el índice después de cambiar el corpus
python scripts/preparar_indice_hf.py
```

## Estructura

```
asistente-fisica/
├── app/                 # FastAPI backend (chat + endpoints del dashboard)
│   └── static/          # HTML/CSS/JS servidos por FastAPI
├── rag/                 # Lógica de RAG
│   ├── loaders/         # PDF → Markdown (pymupdf4llm)
│   ├── splitters/       # Chunking (RecursiveCharacterTextSplitter)
│   ├── retrievers/      # Embeddings + cliente ChromaDB
│   ├── prompts/         # System prompt Socrático
│   ├── chain.py         # Orquestación del pipeline RAG
│   ├── exercises.py     # Catálogo de ejercicios tutor
│   ├── history.py       # Persistencia del historial (Turso + SQLite)
│   ├── history_async.py # Wrapper asíncrono del historial
│   └── topics.py        # Sidebar de unidades y preguntas
├── rag/index/           # Artefactos pre-bakeados para deploy
│   ├── chroma/          # Índice ChromaDB
│   └── hf-model/        # Snapshot del modelo de embeddings (gitignored)
├── dashboard/           # Queries SQL reutilizadas por el dashboard y los tests
├── scripts/             # CLI: indexar_pdfs, preparar_indice_hf, smoke tests, etc.
├── data/                # ChromaDB + SQLite de desarrollo (gitignored)
├── tests/               # Pytest + specs de corridas manuales
├── docs/                # ADRs, runbook de deploy (hf-space.md), guías para Nair
└── AGENTS.md            # Constitución del proyecto (leer primero)
```

## Licencia MIT.

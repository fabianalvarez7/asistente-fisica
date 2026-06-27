"""FastAPI transport layer for the Física 1 chat assistant.

Thin by design: all RAG logic lives in rag/chain.py. This module only wires
HTTP/SSE to the generator and serves the static chat UI.
"""

import os

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag.chain import generate_response
from rag.retrievers import VectorStore

# -----------------------------------------------------------------------------
# Boot assertions — fail fast before accepting traffic
# -----------------------------------------------------------------------------
if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError(
        "GROQ_API_KEY no está configurada. "
        "Set the GROQ_API_KEY environment variable to start the chat server."
    )

_vector_store = VectorStore()
if _vector_store.count() == 0:
    raise RuntimeError(
        f"La colección de ChromaDB está vacía ({_vector_store.persist_dir}). "
        "Indexá los PDFs con scripts/indexar_pdfs.py o configurá "
        "CHROMA_PERSIST_DIR apuntando a un índice con datos."
    )

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="Asistente de Física 1")


class ChatRequest(BaseModel):
    """Body for POST /chat."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Pregunta del estudiante de Física 1",
    )


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    """Stream a RAG-grounded answer via Server-Sent Events."""
    return StreamingResponse(
        generate_response(req.query),
        media_type="text/event-stream",
    )


# Serve the chat UI and its assets. Routes declared above take precedence;
# everything else falls through to the static files mounted at root.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

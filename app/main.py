"""FastAPI transport layer for the Física 1 chat assistant.

Thin by design: all RAG logic lives in rag/chain.py. This module only wires
HTTP/SSE to the generator, serves the static chat UI, and orchestrates the
per-student conversation history persisted by rag/history.py.
"""

from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag.history import (
    init_db,
    get_or_create_student,
    get_student_by_name,
    get_message_owner,
    save_message,
    get_history,
    delete_message,
)
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
# Configuration
# -----------------------------------------------------------------------------
try:
    HISTORY_WINDOW = int(os.getenv("HISTORY_WINDOW", "10"))
except ValueError:
    HISTORY_WINDOW = 10

ERROR_FALLBACK = "Ocurrió un error, intentá de nuevo"

# -----------------------------------------------------------------------------
# Schema init — safe to call repeatedly (CREATE TABLE IF NOT EXISTS)
# -----------------------------------------------------------------------------
init_db()

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
    student_name: str = Field(
        ...,
        min_length=1,
        description="Display name typed by the student. Required — no anonymous chat.",
    )


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    """Stream a RAG-grounded answer via Server-Sent Events.

    Persists the user message before calling Groq, then accumulates the
    assistant response and persists it on [DONE]. On unexpected failures an
    error fallback message is stored as the assistant turn.
    """
    name = req.student_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="student_name cannot be empty")

    student_id = get_or_create_student(name)
    user_message_id = save_message(student_id, "user", req.query)
    history = get_history(student_id, limit=HISTORY_WINDOW)

    def event_generator():
        buffer = ""
        failed = False
        assistant_message_id = None

        yield f"event: user_message_id\ndata: {user_message_id}\n\n"

        try:
            for token in generate_response(req.query, history=history):
                if token.startswith("event: error"):
                    failed = True
                    assistant_message_id = save_message(
                        student_id, "assistant", ERROR_FALLBACK
                    )
                    yield f"event: assistant_message_id\ndata: {assistant_message_id}\n\n"
                    yield token
                    continue

                if token.startswith("data: "):
                    payload = token[6:].removesuffix("\n\n")
                    if payload == "[DONE]":
                        if failed:
                            # The error path already persisted the fallback.
                            pass
                        else:
                            assistant_message_id = save_message(
                                student_id, "assistant", buffer
                            )
                            yield f"event: assistant_message_id\ndata: {assistant_message_id}\n\n"
                        yield token
                        return
                    buffer += payload

                yield token
        except Exception:  # noqa: BLE001
            assistant_message_id = save_message(
                student_id, "assistant", ERROR_FALLBACK
            )
            yield f"event: assistant_message_id\ndata: {assistant_message_id}\n\n"
            yield f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/history")
async def get_history_endpoint(student_name: str):
    """Return all messages for a student, ordered by created_at ASC."""
    name = student_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="student_name cannot be empty")

    student_id = get_student_by_name(name)
    if student_id is None:
        return {"messages": []}

    messages = get_history(student_id)
    return {"messages": messages}


@app.delete("/messages/{message_id}")
async def delete_message_endpoint(message_id: int, student_name: str):
    """Delete a single message if it belongs to the requesting student."""
    name = student_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="student_name cannot be empty")

    message_owner = get_message_owner(message_id)
    if message_owner is None:
        raise HTTPException(status_code=404, detail="message not found")

    requester_id = get_student_by_name(name)
    if requester_id is None or message_owner != requester_id:
        raise HTTPException(status_code=403, detail="not authorized")

    delete_message(message_id, requester_id)
    return {"deleted": True}


# Serve the chat UI and its assets. Routes declared above take precedence;
# everything else falls through to the static files mounted at root.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

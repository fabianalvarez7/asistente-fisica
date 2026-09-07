"""FastAPI transport layer for the Física 1 chat assistant.

Thin by design: all RAG logic lives in rag/chain.py. This module only wires
HTTP/SSE to the generator, serves the static chat UI, and orchestrates the
per-student conversation history persisted by rag/history.py.
"""

from dotenv import load_dotenv
load_dotenv()

import json
import os

from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Load .env into os.environ BEFORE any module that reads env at import time.
# rag.chain creates an OpenAI client at module load with
# os.getenv("GROQ_API_KEY", "") — if .env is loaded AFTER that import, the
# client is built with api_key="" and Groq rejects requests with 401.
# HF Spaces injects env vars directly (no .env file), so this only affects
# local dev.
load_dotenv()
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
from rag.topics import load_topics


# -----------------------------------------------------------------------------
# Helper: parse PRODUCTION env var robustly
# Accepts "1", "true", "yes" (case-insensitive) as truthy. Anything else
# (including empty string, "0", "false", unset) is treated as dev mode.
# This avoids the bug where PRODUCTION=0 accidentally enables prod mode
# because os.getenv returns a non-empty string.
# -----------------------------------------------------------------------------

def _is_production() -> bool:
    return os.getenv("PRODUCTION", "").strip().lower() in ("1", "true", "yes")


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
DB_ERROR_MESSAGE = "No se pudo guardar la conversación. Reintentá en un momento."

# Welcome message persisted as the first assistant turn when a student types a
# new display name. Only fires on first-time identification — students with
# existing history keep their real conversation, not a greeting on every reload.
WELCOME_MESSAGE = "¡Hola, {name}!"

# -----------------------------------------------------------------------------
# Schema init — safe to call repeatedly (CREATE TABLE IF NOT EXISTS)
# -----------------------------------------------------------------------------
try:
    init_db()
except Exception:  # noqa: BLE001
    # Defer the failure to the first request so the endpoint can return a 503
    # or SSE error frame instead of crashing the process at import time.
    print("[history] init_db failed; DB errors will be surfaced per request")

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="Asistente de Física 1")


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Force the browser to revalidate on every request.

    Without this, students browsing the prototype cache the HTML/CSS/JS for
    the session and miss new deploys (since they don't know to hard-refresh).
    HF Spaces doesn't expose its CDN's cache-headers to us, but `no-cache`
    at the origin causes browsers to revalidate and pick up the latest
    build. The cost is one extra round-trip per page load — fine for a
    prototype with low traffic.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.add_middleware(NoCacheMiddleware)


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

    try:
        student_id = get_or_create_student(name)
        user_message_id = save_message(student_id, "user", req.query)
        history = get_history(student_id, limit=HISTORY_WINDOW)
    except Exception as exc:  # noqa: BLE001
        # Dev mode surfaces the real exception so we can diagnose DB issues.
        # In prod (HF Spaces) we keep the generic message.
        if _is_production():
            raise HTTPException(status_code=503, detail=DB_ERROR_MESSAGE)
        raise HTTPException(status_code=503, detail=f"DB error: {exc!r}")

    def event_generator():
        buffer = ""
        failed = False
        assistant_message_id = None
        prod = _is_production()

        def _db_error_frame(exc: Exception) -> str:
            # Dev mode surfaces the real exception; prod keeps the generic
            # fallback so users don't see internals.
            msg = DB_ERROR_MESSAGE if prod else f"DB error: {exc!r}"
            return f"event: error\ndata: {json.dumps({'message': msg})}\n\n"

        yield f"event: user_message_id\ndata: {user_message_id}\n\n"

        try:
            for token in generate_response(req.query, history=history):
                if token.startswith("event: error"):
                    failed = True
                    try:
                        assistant_message_id = save_message(
                            student_id, "assistant", ERROR_FALLBACK
                        )
                    except Exception as exc:  # noqa: BLE001
                        yield _db_error_frame(exc)
                        yield "data: [DONE]\n\n"
                        return
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
                            try:
                                assistant_message_id = save_message(
                                    student_id, "assistant", buffer
                                )
                            except Exception as exc:  # noqa: BLE001
                                yield _db_error_frame(exc)
                                yield "data: [DONE]\n\n"
                                return
                            yield f"event: assistant_message_id\ndata: {assistant_message_id}\n\n"
                        yield token
                        return
                    buffer += payload

                yield token
        except Exception as outer_exc:  # noqa: BLE001
            try:
                assistant_message_id = save_message(
                    student_id, "assistant", ERROR_FALLBACK
                )
            except Exception as inner_exc:  # noqa: BLE001
                # If the outer exception is from the DB, pass it; otherwise
                # the inner one (the DB write failure) is what the user needs.
                yield _db_error_frame(outer_exc if isinstance(outer_exc, Exception) and "save" not in str(outer_exc) else inner_exc)
                yield "data: [DONE]\n\n"
                return
            yield f"event: assistant_message_id\ndata: {assistant_message_id}\n\n"
            yield f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/history")
async def get_history_endpoint(student_name: str):
    """Return all messages for a student, ordered by created_at ASC.

    First-time identification: if the typed name has no student row yet, the
    student is created and a welcome message is persisted as the first
    assistant turn. Subsequent calls with the same name return the existing
    history unchanged.
    """
    name = student_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="student_name cannot be empty")

    try:
        student_id = get_student_by_name(name)
        if student_id is None:
            # First time we see this name: create the student and drop the
            # welcome message into the conversation so it survives reloads.
            student_id = get_or_create_student(name)
            save_message(student_id, "assistant", WELCOME_MESSAGE.format(name=name))

        messages = get_history(student_id)
    except Exception as exc:  # noqa: BLE001
        if _is_production():
            raise HTTPException(status_code=503, detail=DB_ERROR_MESSAGE)
        raise HTTPException(status_code=503, detail=f"DB error: {exc!r}")

    return {"messages": messages}


@app.delete("/messages/{message_id}")
async def delete_message_endpoint(message_id: int, student_name: str):
    """Delete a single message if it belongs to the requesting student."""
    name = student_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="student_name cannot be empty")

    try:
        message_owner = get_message_owner(message_id)
        if message_owner is None:
            raise HTTPException(status_code=404, detail="message not found")

        requester_id = get_student_by_name(name)
        if requester_id is None or message_owner != requester_id:
            raise HTTPException(status_code=403, detail="not authorized")

        delete_message(message_id, requester_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        if _is_production():
            raise HTTPException(status_code=503, detail=DB_ERROR_MESSAGE)
        raise HTTPException(status_code=503, detail=f"DB error: {exc!r}")

    return {"deleted": True}


@app.get("/topics")
async def get_topics():
    """Return the thematic units extracted from the course syllabus PDF.

    Used by the sidebar in the chat UI to show the "índice de temas".
    Failures are treated as decorative: the chat remains usable.
    """
    try:
        unidades = load_topics()
    except Exception as exc:  # noqa: BLE001
        if _is_production():
            raise HTTPException(
                status_code=503,
                detail="No se pudo cargar el índice de temas.",
            )
        raise HTTPException(status_code=503, detail=f"Topics error: {exc!r}")

    return {"unidades": unidades}


# Serve the chat UI and its assets. Routes declared above take precedence;
# everything else falls through to the static files mounted at root.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

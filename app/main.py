"""FastAPI transport layer for the Física 1 chat assistant.

Thin by design: all RAG logic lives in rag/chain.py. This module only wires
HTTP/SSE to the generator, serves the static chat UI, and orchestrates the
per-student conversation history persisted by rag/history.py.
"""

from dotenv import load_dotenv
load_dotenv()

import logging
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
    HistoryUnavailableError,
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


logger = logging.getLogger(__name__)


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

#: SSE ``event:`` name announcing the persistence layer's health for the
#: current request. ``data:`` payload is ``"degraded"`` when at least one
#: history operation failed and the chat is responding without persistence.
#: The frontend uses this to show a non-blocking banner so students know
#: the conversation will not survive a reload but they can keep asking.
HISTORY_STATUS_EVENT = "history_status"
HISTORY_STATUS_DEGRADED = "degraded"

# Welcome message persisted as the first assistant turn when a student types a
# new display name. Only fires on first-time identification — students with
# existing history keep their real conversation, not a greeting on every reload.
WELCOME_MESSAGE = "¡Hola, {name}!"


def _log_history_failure(operation: str, exc: HistoryUnavailableError) -> None:
    """Log persistence degradation without student, chat, or secret data."""
    root_cause = exc.__cause__
    wrapper_type = type(exc).__name__
    root_cause_type = (
        type(root_cause).__name__
        if root_cause is not None
        else wrapper_type
    )
    logger.error(
        "History unavailable; continuing in degraded mode "
        "(operation=%s, wrapper_type=%s, root_cause_type=%s)",
        operation,
        wrapper_type,
        root_cause_type,
    )


# -----------------------------------------------------------------------------
# Schema init — safe to call repeatedly (CREATE TABLE IF NOT EXISTS)
# -----------------------------------------------------------------------------
try:
    init_db()
except HistoryUnavailableError as exc:
    # History is optional for chat availability. Requests will retry through
    # the persistence boundary without switching to another database.
    _log_history_failure("initialize", exc)

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
    assistant response and persists it on [DONE]. History operations degrade
    independently: successful reads and writes remain available while failed
    operations are skipped without blocking the RAG response.

    If any history operation fails for this request, the SSE stream starts
    with ``event: history_status\ndata: degraded\n\n`` so the frontend can
    surface a banner explaining that the conversation will not survive a
    reload but the student can keep asking. The chat itself continues
    normally — only persistence is unavailable.
    """
    name = req.student_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="student_name cannot be empty")

    student_id = None
    user_message_id = None
    history = []
    history_degraded = False

    try:
        student_id = get_or_create_student(name)
    except HistoryUnavailableError as exc:
        _log_history_failure("get_or_create_student", exc)
        history_degraded = True

    if student_id is not None:
        try:
            user_message_id = save_message(student_id, "user", req.query)
        except HistoryUnavailableError as exc:
            _log_history_failure("save_user_message", exc)
            history_degraded = True

        try:
            history = get_history(student_id, limit=HISTORY_WINDOW)
        except HistoryUnavailableError as exc:
            _log_history_failure("read_recent_history", exc)
            history_degraded = True

    def event_generator():
        nonlocal history_degraded
        buffer = ""
        failed = False
        fallback_save_attempted = False

        def fallback_message_id_frame():
            nonlocal fallback_save_attempted
            if student_id is None or fallback_save_attempted:
                return None

            fallback_save_attempted = True
            try:
                assistant_message_id = save_message(
                    student_id, "assistant", ERROR_FALLBACK
                )
            except HistoryUnavailableError as exc:
                _log_history_failure("save_assistant_error", exc)
                return None

            return (
                "event: assistant_message_id\n"
                f"data: {assistant_message_id}\n\n"
            )

        def generation_error_frames():
            message_id_frame = fallback_message_id_frame()
            if message_id_frame is not None:
                yield message_id_frame
            yield f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            yield "data: [DONE]\n\n"

        # Announce degraded history BEFORE the user_message_id so the banner
        # is visible from the very first byte of the response. The frontend
        # is idempotent on this event — re-emitting is a no-op if the
        # banner is already up.
        if history_degraded:
            yield (
                f"event: {HISTORY_STATUS_EVENT}\n"
                f"data: {HISTORY_STATUS_DEGRADED}\n\n"
            )

        if user_message_id is not None:
            yield f"event: user_message_id\ndata: {user_message_id}\n\n"

        try:
            tokens = iter(generate_response(req.query, history=history))
        except Exception:  # noqa: BLE001
            yield from generation_error_frames()
            return

        while True:
            try:
                token = next(tokens)
            except StopIteration:
                return
            except Exception:  # noqa: BLE001
                yield from generation_error_frames()
                return

            if token.startswith("event: error"):
                failed = True
                message_id_frame = fallback_message_id_frame()
                if message_id_frame is not None:
                    yield message_id_frame
                yield token
                continue

            if token.startswith("data: "):
                payload = token[6:].removesuffix("\n\n")
                if payload == "[DONE]":
                    if not failed and student_id is not None:
                        try:
                            assistant_message_id = save_message(
                                student_id, "assistant", buffer
                            )
                        except HistoryUnavailableError as exc:
                            _log_history_failure("save_assistant_message", exc)
                            # Mid-stream degradation: history was OK at
                            # request entry but the assistant write failed.
                            # Re-announce so the banner shows up if it
                            # wasn't visible already.
                            yield (
                                f"event: {HISTORY_STATUS_EVENT}\n"
                                f"data: {HISTORY_STATUS_DEGRADED}\n\n"
                            )
                            history_degraded = True
                        else:
                            yield (
                                "event: assistant_message_id\n"
                                f"data: {assistant_message_id}\n\n"
                            )
                    yield token
                    return
                buffer += payload

            yield token

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

    operation = "lookup_student"
    history_degraded = False
    try:
        student_id = get_student_by_name(name)
        if student_id is None:
            # First time we see this name: create the student and drop the
            # welcome message into the conversation so it survives reloads.
            operation = "create_student"
            student_id = get_or_create_student(name)
            operation = "save_welcome_message"
            try:
                save_message(
                    student_id, "assistant", WELCOME_MESSAGE.format(name=name)
                )
            except HistoryUnavailableError as exc:
                _log_history_failure("save_welcome_message", exc)
                history_degraded = True

        operation = "read_history"
        messages = get_history(student_id)
    except HistoryUnavailableError as exc:
        _log_history_failure(operation, exc)
        messages = []
        history_degraded = True

    return {"messages": messages, "degraded": history_degraded}


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

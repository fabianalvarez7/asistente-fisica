"""FastAPI transport layer for the Física 1 chat assistant.

Thin by design: all RAG logic lives in rag/chain.py. This module only wires
HTTP/SSE to the generator, serves the static chat UI, and orchestrates the
per-student conversation history persisted by rag/history.py.
"""

from contextlib import asynccontextmanager
import asyncio
from functools import partial
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Load .env into os.environ BEFORE any module that reads env at import time.
# rag.chain creates an OpenAI client at module load with
# os.getenv("GROQ_API_KEY", "") — if .env is loaded AFTER that import, the
# client is built with api_key="" and Groq rejects requests with 401.
# HF Spaces injects env vars directly (no .env file), so this only affects
# local dev.
load_dotenv()
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dashboard.queries import get_kpis, get_topic_counts

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
from rag.history_async import (
    DEFAULT_HISTORY_TIMEOUT_SECONDS,
    Deadline,
    bounded_call,
    enqueue_write,
    get_write_worker,
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


def _parse_history_timeout(raw: str | None) -> float:
    """Parse the history availability budget without making startup fragile."""
    try:
        value = (
            float(raw)
            if raw is not None
            else DEFAULT_HISTORY_TIMEOUT_SECONDS
        )
    except (TypeError, ValueError):
        return DEFAULT_HISTORY_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_HISTORY_TIMEOUT_SECONDS


HISTORY_TIMEOUT_SECONDS = _parse_history_timeout(
    os.getenv("HISTORY_TIMEOUT_SECONDS")
)

ERROR_FALLBACK = "Ocurrió un error, intentá de nuevo"
DB_ERROR_MESSAGE = "No se pudo guardar la conversación. Reintentá en un momento."
DASHBOARD_ERROR_MESSAGE = (
    "No se pudieron cargar las métricas en este momento. Intentá nuevamente más tarde."
)
_DASHBOARD_HTML = Path(__file__).resolve().parent / "static" / "dashboard.html"

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


def _log_write_observation_failure(operation: str) -> None:
    """Use the existing redacted degradation log for async write outcomes."""
    _log_history_failure(operation, HistoryUnavailableError("write unavailable"))


def _queued_save_message(student_id: int, role: str, content: str):
    """Keep already-classified history failures terminal at the queue edge."""
    try:
        return save_message(student_id, role, content)
    except HistoryUnavailableError as exc:
        # The sync boundary attaches the original driver error as __cause__.
        # A cause-less wrapper is already classified/exhausted and must not
        # consume a later queued turn during retry-in-place backoff.
        if exc.__cause__ is None:
            return None
        raise


def _enqueue_history_write(fn, /, *args):
    """Enqueue persistence using the same budget as awaited history calls."""
    return enqueue_write(fn, *args, call_timeout=HISTORY_TIMEOUT_SECONDS)


def _next_token(tokens):
    """Pull one token in a worker thread without leaking StopIteration."""
    try:
        return next(tokens), True
    except StopIteration:
        return None, False


# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Bootstrap history without allowing persistence to block app startup."""
    try:
        await bounded_call(init_db, timeout=HISTORY_TIMEOUT_SECONDS)
    except HistoryUnavailableError as exc:
        _log_history_failure("initialize", exc)

    get_write_worker(call_timeout=HISTORY_TIMEOUT_SECONDS).ensure_running()
    try:
        yield
    finally:
        await get_write_worker(call_timeout=HISTORY_TIMEOUT_SECONDS).shutdown()

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title="Asistente de Física 1", lifespan=lifespan)


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

    deadline = Deadline(HISTORY_TIMEOUT_SECONDS).start()
    student_id = None
    user_message_id = None
    user_write_timed_out = False
    history = []
    history_degraded = False

    try:
        student_id = await bounded_call(
            get_or_create_student, name, timeout=deadline.left
        )
    except HistoryUnavailableError as exc:
        _log_history_failure("get_or_create_student", exc)
        history_degraded = True

    if student_id is not None:
        user_pending = _enqueue_history_write(
            _queued_save_message, student_id, "user", req.query
        )
        user_message_id = await user_pending.resolve(deadline.left)
        user_write_timed_out = (
            user_message_id is None and not user_pending.future.done()
        )
        if user_message_id is None:
            _log_write_observation_failure("save_user_message")
            history_degraded = True

        try:
            history = await bounded_call(
                partial(get_history, student_id, limit=HISTORY_WINDOW),
                timeout=deadline.left,
            )
        except HistoryUnavailableError as exc:
            _log_history_failure("read_recent_history", exc)
            history_degraded = True

    async def event_generator():
        nonlocal history_degraded
        buffer = ""
        failed = False
        fallback_save_attempted = False

        async def fallback_message_id_frame():
            nonlocal fallback_save_attempted
            if student_id is None or fallback_save_attempted:
                return None

            fallback_save_attempted = True
            fallback_pending = _enqueue_history_write(
                _queued_save_message, student_id, "assistant", ERROR_FALLBACK
            )
            assistant_message_id = await fallback_pending.resolve(
                HISTORY_TIMEOUT_SECONDS
            )
            if assistant_message_id is None:
                _log_write_observation_failure("save_assistant_error")
                return None

            return (
                "event: assistant_message_id\n"
                f"data: {assistant_message_id}\n\n"
            )

        async def generation_error_frames():
            message_id_frame = await fallback_message_id_frame()
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
            async for frame in generation_error_frames():
                yield frame
            return

        while True:
            try:
                token, has_token = await asyncio.to_thread(_next_token, tokens)
                if not has_token:
                    return
            except Exception:  # noqa: BLE001
                async for frame in generation_error_frames():
                    yield frame
                return

            if token.startswith("event: error"):
                failed = True
                message_id_frame = await fallback_message_id_frame()
                if message_id_frame is not None:
                    yield message_id_frame
                yield token
                continue

            if token.startswith("data: "):
                payload = token[6:].removesuffix("\n\n")
                if payload == "[DONE]":
                    if not failed and student_id is not None:
                        assistant_pending = _enqueue_history_write(
                            _queued_save_message, student_id, "assistant", buffer
                        )
                        if not user_write_timed_out:
                            assistant_message_id = await assistant_pending.resolve(
                                HISTORY_TIMEOUT_SECONDS
                            )
                            if assistant_message_id is None:
                                _log_write_observation_failure(
                                    "save_assistant_message"
                                )
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
    deadline = Deadline(HISTORY_TIMEOUT_SECONDS).start()
    try:
        student_id = await bounded_call(
            get_student_by_name, name, timeout=deadline.left
        )
        if student_id is None:
            # First time we see this name: create the student and drop the
            # welcome message into the conversation so it survives reloads.
            operation = "create_student"
            student_id = await bounded_call(
                get_or_create_student, name, timeout=deadline.left
            )
            operation = "save_welcome_message"
            welcome_pending = _enqueue_history_write(
                _queued_save_message,
                student_id,
                "assistant",
                WELCOME_MESSAGE.format(name=name),
            )
            welcome_message_id = await welcome_pending.resolve(deadline.left)
            if welcome_message_id is None:
                _log_write_observation_failure("save_welcome_message")
                history_degraded = True

        operation = "read_history"
        messages = await bounded_call(
            get_history, student_id, timeout=deadline.left
        )
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

    deadline = Deadline(HISTORY_TIMEOUT_SECONDS).start()
    try:
        message_owner = await bounded_call(
            get_message_owner, message_id, timeout=deadline.left
        )
        if message_owner is None:
            raise HTTPException(status_code=404, detail="message not found")

        requester_id = await bounded_call(
            get_student_by_name, name, timeout=deadline.left
        )
        if requester_id is None or message_owner != requester_id:
            raise HTTPException(status_code=403, detail="not authorized")

        await bounded_call(
            delete_message, message_id, requester_id, timeout=deadline.left
        )
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


@app.get("/api/dashboard")
async def get_dashboard_data():
    """Return the anonymous aggregate data used by the public dashboard.

    The query module owns all database access and classification logic. This
    transport layer deliberately selects only the approved public fields so a
    future query change cannot accidentally expose message text or identifiers.
    """
    try:
        deadline = Deadline(HISTORY_TIMEOUT_SECONDS).start()
        kpis = await bounded_call(get_kpis, timeout=deadline.left)
        topic_counts = await bounded_call(get_topic_counts, timeout=deadline.left)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Public dashboard unavailable (error_type=%s)",
            type(exc).__name__,
        )
        raise HTTPException(status_code=503, detail=DASHBOARD_ERROR_MESSAGE) from exc

    return {
        "total_questions": kpis["total_queries"],
        "students_represented": kpis["unique_students"],
        "latest_activity": kpis["last_activity"],
        "topic_counts": [
            {
                "number": item["number"],
                "title": item["title"],
                "count": item["count"],
            }
            for item in topic_counts
        ],
        "topic_counts_approximate": True,
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    """Serve the read-only public dashboard without requiring Streamlit."""
    return FileResponse(_DASHBOARD_HTML)


# Serve the chat UI and its assets. Routes declared above take precedence;
# everything else falls through to the static files mounted at root.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

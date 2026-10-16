"""RAG orchestration chain.

Thin composition layer (AGENTS.md §7 decision 9): embed → retrieve →
threshold → prompt → Groq SSE stream. Keeps all RAG logic out of FastAPI.

The theory-mode Groq call injects a static few-shot message block before the
live query so the model sees concrete Socratic user/assistant turns without
bloating the system prompt. Exercise mode is limited to its curated scope.
"""

import os
from typing import Generator

from openai import OpenAI

from rag.exercises import Exercise, plain_text
from rag.prompts import SYSTEM_PROMPT
from rag.retrievers import EmbeddingsModel, VectorStore


def _is_production() -> bool:
    """Parse PRODUCTION env var robustly. Accepts '1'/'true'/'yes' (case-insensitive)
    as truthy; anything else (empty, '0', 'false', unset) is dev mode. Avoids the
    bug where PRODUCTION=0 accidentally enables prod mode because os.getenv
    returns a non-empty string."""
    return os.getenv("PRODUCTION", "").strip().lower() in ("1", "true", "yes")


# Module-level singletons. EmbeddingsModel lazy-loads the transformer on first
# use; VectorStore/ChromaDB reads are thread-safe. No per-request mutable state.
_OPENAI_CLIENT = OpenAI(
    api_key=os.getenv("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1",
)
_EMBEDDINGS = EmbeddingsModel()
_VECTOR_STORE = VectorStore()

_DEFAULT_MODEL = "openai/gpt-oss-120b"
_DISTANCE_THRESHOLD = 0.5  # cosine distance; distance <= 0.5 => cos_sim >= 0.5
_NO_CONTEXT_FALLBACK = "No encuentro info sobre esto en los apuntes"
_FALLBACK_ERROR = "Ocurrió un error, intentá de nuevo"
EXERCISE_PROGRESS_ERROR = (
    "No se pudo leer tu progreso. No se generó una nueva guía. Reintentá."
)

# Few-shot Socratic examples: 3 user/assistant pairs spanning error theory,
# kinematics, and dynamics. Each assistant turn uses Rioplatense voseo, ends
# with a guiding question, and never gives a final numerical answer.
_FEW_SHOT = [
    {
        "role": "user",
        "content": "¿Cuál es la fórmula del error relativo porcentual?",
    },
    {
        "role": "assistant",
        "content": (
            "Antes de darte la fórmula, pensemos juntos. El error relativo "
            "porcentual sirve para comparar el error absoluto con el valor "
            "medido. ¿Qué operación se te ocurre entre el error absoluto y el "
            "valor verdadero para expresar esa comparación?"
        ),
    },
    {
        "role": "user",
        "content": (
            "Un auto frena de 60 km/h a 0 en 5 segundos. "
            "¿Cuánto vale la aceleración?"
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Buen problema. Antes de calcular nada, identifiquemos los datos. "
            "¿Podés listar la velocidad inicial, la velocidad final y el tiempo "
            "que tardó en frenar? Una vez que los tengas, ¿qué ecuación de "
            "cinemática relaciona esas tres variables con la aceleración?"
        ),
    },
    {
        "role": "user",
        "content": (
            "No entiendo cómo aplicar las leyes de Newton a un bloque sobre "
            "un plano inclinado."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "Tranquilo, vamos de a poco. Cuando tenés un cuerpo sobre un plano "
            "inclinado, conviene descomponer las fuerzas en direcciones "
            "paralelas y perpendiculares al plano. ¿Qué fuerzas actúan sobre el "
            "bloque y en qué direcciones las dibujarías?"
        ),
    },
]


def _build_context(documents: list) -> str:
    """Join retrieved documents into a single context string."""
    parts = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "desconocido")
        parts.append(f"[Extracto {i} - {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _build_exercise_scope(exercise: Exercise, checkpoint_index: int) -> str:
    """Build controlled scope instructions without exposing the teacher key."""
    concepts = ", ".join(exercise.concepts)
    if checkpoint_index >= len(exercise.checkpoints):
        current_guidance = (
            "El estudiante ya completó los checkpoints. Ayudalo a verificar "
            "sus resultados sin agregar pasos nuevos."
        )
    else:
        checkpoint = exercise.checkpoints[max(checkpoint_index, 0)]
        current_guidance = (
            f"Checkpoint actual ({checkpoint.id}): {plain_text(checkpoint.prompt)}\n"
            f"Ayuda permitida para este punto: {plain_text(checkpoint.hint)}"
        )
    return (
        f"ID: {exercise.id}\n"
        f"Título: {exercise.title}\n"
        f"Enunciado controlado: {plain_text(exercise.statement)}\n"
        f"Conceptos permitidos: {concepts}\n"
        f"{current_guidance}\n"
        "No resuelvas otro ejercicio ni completes este ejercicio por el estudiante. "
        "Si la pregunta se sale de este enunciado, responde exactamente: "
        '"No encuentro info sobre esto en los apuntes".'
    )


def generate_response(
    query: str,
    history: list[dict] | None = None,
    *,
    exercise: Exercise | None = None,
    checkpoint_index: int | None = None,
) -> Generator[str, None, None]:
    """Orchestrate RAG pipeline and stream Groq tokens as SSE frames.

    Input contract:
      - query: non-empty str, max 500 chars (validated by FastAPI).
      - history: optional list of {"role": ..., "content": ...} dicts from
        SQLite, ordered chronologically. Injected between _FEW_SHOT and the
        current query. None or [] means single-turn (no history).
       - exercise: selected curated exercise for exercise mode. ``None`` keeps
         the existing course-wide theory-chat behavior.
      - checkpoint_index: canonical next checkpoint index for exercise mode.
        It is never inferred from chat history. ``None`` fails closed.
      - GROQ_API_KEY is assumed present (guaranteed by app/main.py boot check).
      - ChromaDB collection is assumed non-empty (guaranteed by app/main.py).

    Output contract:
      - Yields complete SSE frames:
          data: <token>\n\n
          event: error\ndata: <msg>\n\n
          data: [DONE]\n\n
       - Theory no-context fallback: if best cosine_dist > 0.5, yields a single
         data: "No encuentro info sobre esto en los apuntes" frame, then
         data: [DONE]. Groq is NEVER called. Exercise mode uses only the
         selected exercise's curated scope.
      - Always terminates with data: [DONE].

    Exception contract:
      - NEVER raises. All exceptions are caught and converted to error frames,
        then the generator ends with data: [DONE].
    """
    try:
        if exercise is None:
            query_embedding = _EMBEDDINGS.embed_query(query)
            scored_docs = _VECTOR_STORE.similarity_search_with_scores(
                query_embedding, k=4
            )
            if not scored_docs or scored_docs[0][1] > _DISTANCE_THRESHOLD:
                yield f"data: {_NO_CONTEXT_FALLBACK}\n\n"
                yield "data: [DONE]\n\n"
                return

            documents = [doc for doc, _ in scored_docs]
            context = _build_context(documents)
            exercise_scope = (
                "No hay un ejercicio curado seleccionado. "
                "Aplicá únicamente las reglas RAG generales."
            )
        else:
            if checkpoint_index is None:
                yield f"event: error\ndata: {EXERCISE_PROGRESS_ERROR}\n\n"
                yield "data: [DONE]\n\n"
                return
            # Exercise mode is deliberately independent from the global course
            # index. This scope is the only context allowed for the selected
            # published exercise.
            context = _build_exercise_scope(exercise, checkpoint_index)
            exercise_scope = context
        prompt = SYSTEM_PROMPT.format(
            context=context,
            exercise_scope=exercise_scope,
        )

        messages = [
            {"role": "system", "content": prompt},
            *(_FEW_SHOT if exercise is None else []),
        ]
        if history:
            # Project to {role, content} only: get_history() returns SQLite
            # rows that include `id` and `created_at` for the persistence layer,
            # but Groq's chat API rejects any extra fields per message object.
            messages.extend(
                {"role": m["role"], "content": m["content"]} for m in history
            )
        messages.append({"role": "user", "content": query})

        if not _is_production():
            # Manual review gate: dump assembled message list for eyeball verification.
            for i, msg in enumerate(messages):
                role = msg["role"]
                preview = msg["content"][:80].replace("\n", " ")
                print(f"[MSG {i:02d}] {role:9s} | {preview}...")

        model = os.getenv("LLM_MODEL", _DEFAULT_MODEL)
        stream = _OPENAI_CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.0,
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content if delta else None
            if content:
                yield f"data: {content}\n\n"

    except Exception as exc:  # noqa: BLE001
        # Dev mode surfaces the real exception so we can diagnose Groq errors
        # without enabling PRODUCTION. In prod we keep the generic fallback.
        if _is_production():
            yield f"event: error\ndata: {_FALLBACK_ERROR}\n\n"
        else:
            yield f"event: error\ndata: {exc}\n\n"

    yield "data: [DONE]\n\n"

"""RAG orchestration chain.

Thin composition layer (AGENTS.md §7 decision 9): embed → retrieve →
threshold → prompt → Groq SSE stream. Keeps all RAG logic out of FastAPI.

The Groq call injects a static few-shot message block before the live query
so the model sees concrete Socratic user/assistant turns without bloating the
system prompt.
"""

import os
from typing import Generator

from openai import OpenAI

from rag.prompts import SYSTEM_PROMPT
from rag.retrievers import EmbeddingsModel, VectorStore

# Module-level singletons. EmbeddingsModel lazy-loads the transformer on first
# use; VectorStore/ChromaDB reads are thread-safe. No per-request mutable state.
_OPENAI_CLIENT = OpenAI(
    api_key=os.getenv("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1",
)
_EMBEDDINGS = EmbeddingsModel()
_VECTOR_STORE = VectorStore()

_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_DISTANCE_THRESHOLD = 0.5  # cosine distance; distance <= 0.5 => cos_sim >= 0.5
_NO_CONTEXT_FALLBACK = "No encuentro info sobre esto en los apuntes"

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


def generate_response(
    query: str,
    history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """Orchestrate RAG pipeline and stream Groq tokens as SSE frames.

    Input contract:
      - query: non-empty str, max 500 chars (validated by FastAPI).
      - history: optional list of {"role": ..., "content": ...} dicts from
        SQLite, ordered chronologically. Injected between _FEW_SHOT and the
        current query. None or [] means single-turn (no history).
      - GROQ_API_KEY is assumed present (guaranteed by app/main.py boot check).
      - ChromaDB collection is assumed non-empty (guaranteed by app/main.py).

    Output contract:
      - Yields complete SSE frames:
          data: <token>\n\n
          event: error\ndata: <msg>\n\n
          data: [DONE]\n\n
      - No-context fallback: if best cosine_dist > 0.5, yields a single
        data: "No encuentro info sobre esto en los apuntes" frame, then
        data: [DONE]. Groq is NEVER called.
      - Always terminates with data: [DONE].

    Exception contract:
      - NEVER raises. All exceptions are caught and converted to error frames,
        then the generator ends with data: [DONE].
    """
    try:
        query_embedding = _EMBEDDINGS.embed_query(query)
        scored_docs = _VECTOR_STORE.similarity_search_with_scores(query_embedding, k=4)

        if not scored_docs or scored_docs[0][1] > _DISTANCE_THRESHOLD:
            yield f"data: {_NO_CONTEXT_FALLBACK}\n\n"
            yield "data: [DONE]\n\n"
            return

        documents = [doc for doc, _ in scored_docs]
        context = _build_context(documents)
        prompt = SYSTEM_PROMPT.format(context=context)

        messages = [
            {"role": "system", "content": prompt},
            *_FEW_SHOT,
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})

        if not os.getenv("PRODUCTION"):
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
        yield f"event: error\ndata: {exc}\n\n"

    yield "data: [DONE]\n\n"

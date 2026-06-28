"""RAG orchestration chain.

Thin composition layer (AGENTS.md §7 decision 9): embed → retrieve →
threshold → prompt → Groq SSE stream. Keeps all RAG logic out of FastAPI.
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


def _build_context(documents: list) -> str:
    """Join retrieved documents into a single context string."""
    parts = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "desconocido")
        parts.append(f"[Extracto {i} - {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def generate_response(query: str) -> Generator[str, None, None]:
    """Orchestrate RAG pipeline and stream Groq tokens as SSE frames.

    Input contract:
      - query: non-empty str, max 500 chars (validated by FastAPI).
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

        model = os.getenv("LLM_MODEL", _DEFAULT_MODEL)
        stream = _OPENAI_CLIENT.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
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

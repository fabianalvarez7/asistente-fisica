"""Retrievers: embeddings + vector store. Punto de entrada:
EmbeddingsModel y VectorStore."""

from rag.retrievers.embeddings import EmbeddingsModel, DEFAULT_MODEL_NAME
from rag.retrievers.vector_store import VectorStore, DEFAULT_COLLECTION

__all__ = [
    "EmbeddingsModel",
    "VectorStore",
    "DEFAULT_MODEL_NAME",
    "DEFAULT_COLLECTION",
]

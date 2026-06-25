"""Vector store: ChromaDB persistente para RAG.

Envuelve ChromaDB con una interfaz simple y reutilizable. La persistencia
va a CHROMA_PERSIST_DIR (default ./data/chroma/).

Decisión documentada en AGENTS.md sección 7: ChromaDB local, no managed
service. Para un prototipo es lo correcto. Si el corpus crece, ChromaDB
tiene modo client/server.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import chromadb
from chromadb import PersistentClient
from chromadb.config import Settings
from langchain_core.documents import Document

DEFAULT_PERSIST_DIR = "./data/chroma"
DEFAULT_COLLECTION = "asistente_fisica"


class VectorStore:
    """Wrapper de ChromaDB persistente."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = DEFAULT_COLLECTION,
    ):
        self.persist_dir = Path(persist_dir or os.getenv("CHROMA_PERSIST_DIR", DEFAULT_PERSIST_DIR))
        self.collection_name = collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client: PersistentClient | None = None
        self._collection = None

    def _get_client(self) -> PersistentClient:
        if self._client is None:
            self._client = PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )
        return self._client

    @property
    def collection(self):
        """Colección de ChromaDB. Se crea la primera vez."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(self.collection_name)
        return self._collection

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ) -> int:
        """Agrega Documents con sus embeddings al store.

        Args:
            documents: Lista de Documents (de langchain).
            embeddings: Lista de embeddings (uno por Document, misma longitud).

        Returns:
            Cantidad de documentos agregados.
        """
        if not documents:
            return 0
        if len(documents) != len(embeddings):
            raise ValueError(
                f"documents ({len(documents)}) y embeddings ({len(embeddings)}) "
                f"deben tener la misma longitud"
            )

        ids = []
        metadatas = []
        texts = []
        for i, doc in enumerate(documents):
            # ID estable basado en source + chunk_index
            source = doc.metadata.get("source", "unknown")
            chunk_idx = doc.metadata.get("chunk_index", i)
            doc_id = f"{Path(source).stem}::{chunk_idx}"
            ids.append(doc_id)
            metadatas.append(doc.metadata)
            texts.append(doc.page_content)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts,
        )
        return len(documents)

    def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 4,
    ) -> list[Document]:
        """Busca los k Documents más similares a un embedding de consulta.

        Args:
            query_embedding: Embedding de la consulta (de EmbeddingsModel.embed_query).
            k: Cantidad de resultados a devolver.

        Returns:
            Lista de Documents ordenados por similaridad (más similar primero).
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )
        documents = []
        if not results["documents"]:
            return documents
        for i, text in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            documents.append(Document(page_content=text, metadata=metadata))
        return documents

    def count(self) -> int:
        """Cantidad de documentos indexados."""
        return self.collection.count()

    def reset(self) -> None:
        """Borra la colección completa. Útil para re-indexar desde cero."""
        client = self._get_client()
        client.delete_collection(self.collection_name)
        self._collection = None

    def wipe_disk(self) -> None:
        """Borra la persistencia en disco. CUIDADO: destructivo."""
        if self.persist_dir.exists():
            shutil.rmtree(self.persist_dir)
        self._client = None
        self._collection = None
        self.persist_dir.mkdir(parents=True, exist_ok=True)

"""Embeddings wrapper sobre sentence-transformers.

Carga el modelo multilingüe de HuggingFace una sola vez (singleton)
y expone una interfaz compatible con ChromaDB.

Modelo: intfloat/multilingual-e5-small
- 270MB, ~384 dimensiones
- Soporta español nativo
- Corre en MPS (Mac), CUDA (Windows con GPU) o CPU
- Selección documentada en AGENTS.md sección 4
"""

import os
from typing import Optional

from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-small"
DEFAULT_DEVICE = "auto"

# Resolucion de device
def _resolve_device(device: str) -> str:
    """Mapea 'auto' al device disponible: mps > cuda > cpu."""
    if device != "auto":
        return device
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class EmbeddingsModel:
    """Wrapper de sentence-transformers con interfaz compatible ChromaDB."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: Optional[str] = None,
    ):
        if device is None:
            device = os.getenv("EMBEDDINGS_DEVICE", DEFAULT_DEVICE)
        self.model_name = model_name
        self.device = _resolve_device(device)
        self._model: SentenceTransformer | None = None

    def _load(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    @property
    def model(self) -> SentenceTransformer:
        """Acceso lazy al modelo (carga en el primer uso)."""
        return self._load()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds de una lista de documentos. Para indexar en ChromaDB."""
        model = self._load()
        # E5 espera prefijos: "passage: " para documentos
        prefixed = [f"passage: {t}" for t in texts]
        vectors = model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed de una consulta. Para similarity_search."""
        model = self._load()
        # E5 espera "query: " para queries
        vector = model.encode(
            f"query: {text}",
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()

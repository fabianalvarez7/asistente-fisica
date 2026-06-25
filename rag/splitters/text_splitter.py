"""Text splitters: parten los Documents en chunks para embeddings.

Usa RecursiveCharacterTextSplitter de langchain-text-splitters, que
respeta la jerarquía de separadores (párrafo > oración > palabra)
para no cortar texto arbitrariamente.

Trade-off conocido: las fórmulas LaTeX en display (`$$...$$`) pueden
cortarse si son más largas que chunk_size. Aceptable para el prototipo
porque las fórmulas del cuadernillo son cortas. Si en el futuro hay
fórmulas largas, evaluar MarkdownTextSplitter o agregar `$$` a los
separadores.
"""

from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def split_documents(
    documents: Iterable[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """Parte una lista de Documents en chunks de tamaño aproximado.

    Args:
        documents: Documents a partir (vienen de rag/loaders/).
        chunk_size: Tamaño aproximado del chunk en caracteres.
        chunk_overlap: Cantidad de caracteres superpuestos entre chunks.

    Returns:
        Lista de Documents más chicos. Cada uno hereda la metadata
        del Document original y agrega 'chunk_index' y 'chunk_count'
        para saber la posición dentro del documento original.
    """
    documents = list(documents)
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Separadores por default: ["\n\n", "\n", " ", ""]
        # Prioriza partir por párrafos antes que por oraciones.
    )

    split_docs = splitter.split_documents(documents)
    return split_docs

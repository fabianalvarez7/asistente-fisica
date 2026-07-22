"""PDF loader: convierte PDFs a Markdown para indexar en ChromaDB.

Usa pymupdf4llm (PyMuPDF) porque es rápido y el cuadernillo del curso es
suficientemente limpio para indexar. marker-pdf sigue en requirements.txt
como plan B si Nair necesita mayor fidelidad de fórmulas en LaTeX en el
futuro, pero el cambio de carga de marker a PyMuPDF fue necesario porque
marker-pdf se colgó al 96 %% del cuadernillo después de ~20 min.

Decisión documentada en docs/adr/0001-pdf-loader-marker.md (actualizar si se
estabiliza el loader definitivo).
"""

from pathlib import Path
from typing import Union

import pymupdf4llm
from langchain_core.documents import Document


def load_pdf(path: Union[str, Path]) -> list[Document]:
    """Lee un PDF y devuelve un único Document con todo el markdown.

    Por simplicidad, no partimos por página: el chunker en
    rag/splitters/ se encarga de partir el markdown después con su
    propia estrategia.

    Args:
        path: Ruta al archivo PDF.

    Returns:
        Lista con un único Document:
          - page_content: markdown del PDF completo
          - metadata: { 'source': str(path) }
    """
    path = Path(path)
    markdown = pymupdf4llm.to_markdown(str(path))
    return [
        Document(
            page_content=markdown,
            metadata={"source": str(path)},
        )
    ]


def load_pdfs(paths: list[Union[str, Path]]) -> list[Document]:
    """Lee varios PDFs y concatena los Documents resultantes.

    Args:
        paths: Lista de rutas a archivos PDF.

    Returns:
        Lista de Documents, uno por PDF.
    """
    documents = []
    for path in paths:
        documents.extend(load_pdf(path))
    return documents

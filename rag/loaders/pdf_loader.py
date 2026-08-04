"""PDF loader: converts PDFs to Markdown for ChromaDB indexing.

Uses marker-pdf for LaTeX formula extraction. The PdfConverter and its
model dictionary are loaded once as a module-level singleton so the
multi-minute model warmup is amortized across all PDFs in a re-bake.

See docs/adr/0001-pdf-loader-marker.md for historical context and the
marker-pdf-loader change proposal for the current rationale.
"""

from pathlib import Path
from typing import Union

from langchain_core.documents import Document
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

_CONVERTER: PdfConverter | None = None


def _get_converter() -> PdfConverter:
    """Return a cached PdfConverter, creating it on first call."""
    global _CONVERTER
    if _CONVERTER is None:
        _CONVERTER = PdfConverter(
            artifact_dict=create_model_dict(),
            config={"disable_image_extraction": True},
        )
    return _CONVERTER


def load_pdf(path: Union[str, Path]) -> list[Document]:
    """Read a PDF and return a single Document with the full markdown.

    The chunker in rag/splitters/ handles splitting the markdown later.

    Args:
        path: Path to the PDF file.

    Returns:
        A list with exactly one Document:
          - page_content: marker-pdf rendered markdown (text + LaTeX)
          - metadata: {"source": str(path)}
    """
    path = Path(path)
    converter = _get_converter()
    result = converter(str(path))
    markdown = result.markdown
    return [
        Document(
            page_content=markdown,
            metadata={"source": str(path)},
        )
    ]


def load_pdfs(paths: list[Union[str, Path]]) -> list[Document]:
    """Read multiple PDFs and concatenate the resulting Documents.

    Args:
        paths: List of PDF file paths.

    Returns:
        A list of Documents, one per PDF.
    """
    documents = []
    for path in paths:
        documents.extend(load_pdf(path))
    return documents

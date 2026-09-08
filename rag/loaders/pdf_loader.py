"""PDF loader: converts PDFs to Markdown for ChromaDB indexing.

Uses pymupdf4llm for fast Markdown extraction with inline LaTeX
preservation. Supersedes the marker-pdf approach (ADR 0001).

Marker-pdf was abandoned because its text-recognition step was
prohibitively slow for our corpus (text-recognition alone projected
to ~66 days for the four new PDFs on consumer hardware). pymupdf4llm
extracts text and inline LaTeX in seconds; the tradeoff is that
rendered formula images (formulas-as-pictures in the source PDF) are
not recovered. For our use case (Socratic chat assistant grounded
in course PDFs), this is acceptable: the assistant is a guide, not
a formula-OCR service, and `data/markdown/formulas.md` supplements
the gap.

See docs/adr/0002-pdf-loader-pymupdf4llm.md for the full rationale.
"""

from pathlib import Path
from typing import Union

import pymupdf4llm
from langchain_core.documents import Document


def load_pdf(path: Union[str, Path]) -> list[Document]:
    """Read a PDF and return a single Document with the full markdown.

    The chunker in rag/splitters/ handles splitting the markdown later.

    Args:
        path: Path to the PDF file.

    Returns:
        A list with exactly one Document:
          - page_content: pymupdf4llm-rendered markdown (text + inline LaTeX)
          - metadata: {"source": str(path)}
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
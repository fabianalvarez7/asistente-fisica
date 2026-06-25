"""PDF loader: convierte PDFs a Markdown para indexar en ChromaDB.

Usa marker-pdf (datalab) con OCR + extracción de fórmulas en LaTeX.
Decisión arquitectónica documentada en docs/adr/0001-pdf-loader-marker.md.

Trade-off conocido: marker es ~5-10x más lento que pymupdf4llm,
pero rescata fórmulas en LaTeX que de otro modo se perderían.
Los modelos (surya, texify) se descargan en el primer uso (~3GB)
y se cachean en ~/Library/Caches/datalab/models/.

Para un corpus de 5-10 páginas, la primera indexación tarda ~10 min
en Mac con MPS. Re-indexaciones son infrecuentes (solo cuando cambia
el material).
"""

from pathlib import Path
from typing import Union

from langchain_core.documents import Document
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

# Singleton: los modelos son pesados (~3GB en memoria).
# No los recargamos en cada llamada a load_pdf().
_CONVERTER: PdfConverter | None = None


def _get_converter() -> PdfConverter:
    """Devuelve el converter de marker, creándolo la primera vez."""
    global _CONVERTER
    if _CONVERTER is None:
        artifact_dict = create_model_dict()
        _CONVERTER = PdfConverter(
            artifact_dict=artifact_dict,
            config={
                "output_format": "markdown",
                "disable_image_extraction": True,
            },
        )
    return _CONVERTER


def load_pdf(path: Union[str, Path]) -> list[Document]:
    """Lee un PDF y devuelve un único Document con todo el markdown.

    Por simplicidad, no partimos por página: el chunker en
    rag/splitters/ se encarga de partir el markdown después con su
    propia estrategia. Si en el futuro hace falta saber la página
    exacta de cada chunk, agregar paginate_output=True y partir por
    el separador que produce marker.

    Args:
        path: Ruta al archivo PDF.

    Returns:
        Lista con un único Document:
          - page_content: markdown del PDF completo (con LaTeX para fórmulas)
          - metadata: { 'source': str(path) }
    """
    path = Path(path)
    converter = _get_converter()
    rendered = converter(str(path))
    return [
        Document(
            page_content=rendered.markdown,
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

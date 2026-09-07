"""Extractor del índice temático del programa de Física 1.

El contenido se lee del PDF "Contenidos Temáticos.pdf" y se parsea una sola
vez por proceso. El resultado queda cacheado en memoria para no repetir la
carga en cada request a /topics.
"""

from __future__ import annotations

import os
import re
from typing import List


def _roman_to_int(roman: str) -> int:
    """Convierte un número romano en entero.

    Soporta los valores que aparecen en el syllabus del curso (I..XII).
    """
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(roman.upper()):
        value = values.get(char, 0)
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total


# Cache del índice parseado. Se invalida solo al reiniciar el proceso.
_TOPICS_CACHE: List[dict] | None = None


def load_topics(pdf_path: str | None = None) -> List[dict]:
    """Carga y parsea las unidades temáticas del PDF del programa.

    Args:
        pdf_path: Ruta al PDF. Si es None, se usa la ruta por defecto relativa
            a la raíz del repositorio: ``data/pdfs/Contenidos Temáticos.pdf``.

    Returns:
        Lista ordenada de diccionarios con ``numero`` (int) y ``titulo`` (str).

    Raises:
        RuntimeError: si el PDF no existe o no contiene unidades reconocibles.
    """
    global _TOPICS_CACHE  # noqa: PLW0603

    if _TOPICS_CACHE is not None:
        return _TOPICS_CACHE

    if pdf_path is None:
        pdf_path = os.path.join("data", "pdfs", "Contenidos Temáticos.pdf")

    try:
        import pymupdf4llm
    except ImportError as exc:  # pragma: no cover - controlado en deploy
        raise RuntimeError("pymupdf4llm no está disponible") from exc

    markdown = pymupdf4llm.to_markdown(pdf_path)

    # Ejemplos de formato encontrados en el documento:
    #   "UNIDAD I: Introducción a la Física"
    #   "UNIDAD V:Trabajo y energía"  (sin espacio tras el dos puntos)
    pattern = re.compile(
        r"UNIDAD\s+([IVXLCDM]+)\s*:?\s*(.+?)(?=\s*UNIDAD\s+[IVXLCDM]+|$)",
        re.IGNORECASE | re.DOTALL,
    )

    units = []
    for roman, title in pattern.findall(markdown):
        units.append(
            {
                "numero": roman.upper(),
                "titulo": title.strip().rstrip(":").strip(),
            }
        )

    if not units:
        raise RuntimeError("No se encontraron unidades en el PDF del programa")

    _TOPICS_CACHE = units
    return units

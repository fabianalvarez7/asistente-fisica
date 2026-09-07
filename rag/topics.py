"""Índice temático del programa de Física 1.

Lista hardcodeada de las 12 unidades temáticas del curso, tomadas del PDF
``data/pdfs/Contenidos Temáticos.pdf`` (UNR — Facultad de Ciencias
Bioquímicas y Farmacéuticas). El PDF vive solo en local; en el deploy
se sirve desde este módulo porque ``data/`` está gitignoreado y
excluido del rsync al Space.

Si el syllabus cambia, editar esta lista y redesplegar. Mantener
sincronizado con el PDF al actualizar.
"""

from __future__ import annotations

from typing import List


_TOPICS: List[dict] = [
    {"numero": "I",    "titulo": "Introducción a la Física"},
    {"numero": "II",   "titulo": "Cinemática de la partícula en una dimensión"},
    {"numero": "III",  "titulo": "Cinemática en dos y tres dimensiones"},
    {"numero": "IV",   "titulo": "Leyes de Newton"},
    {"numero": "V",    "titulo": "Trabajo y energía"},
    {"numero": "VI",   "titulo": "Cinemática y dinámica circular"},
    {"numero": "VII",  "titulo": "Estática de los fluidos"},
    {"numero": "VIII", "titulo": "Dinámica de los fluidos"},
    {"numero": "IX",   "titulo": "Sistema de partículas y conservación del momento lineal"},
    {"numero": "X",    "titulo": "Rotación del cuerpo rígido"},
    {"numero": "XI",   "titulo": "Movimiento oscilatorio"},
    {"numero": "XII",  "titulo": "Movimiento ondulatorio"},
]


def load_topics() -> List[dict]:
    """Devuelve las unidades del syllabus para el sidebar.

    Mantenido como función para no romper el contrato con el endpoint
    ``GET /topics`` que importa este símbolo. Devuelve la lista estática
    directamente — no hay parsing ni I/O en runtime.
    """
    return _TOPICS

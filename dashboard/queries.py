"""Pure aggregation queries for the professor dashboard.

This module is UI-agnostic: it only reads from the history database and
returns plain Python dicts/lists. Streamlit-specific code lives in
``dashboard/app.py``.

All aggregates are anonymous: no ``student_id`` or ``display_name`` is
included in the returned data. Queries are grouped by exact ``content`` to
count how many times a given question was asked, without revealing who
asked it.
"""

from __future__ import annotations

from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
from typing import List

# Streamlit runs ``streamlit run dashboard/app.py`` with cwd set to the
# script's directory (i.e. ``dashboard/``), so a plain ``from rag.history
# import ...`` fails because ``rag/`` is a sibling of ``dashboard/`` rather
# than a child. Adding the repo root to ``sys.path`` here lets the module
# resolve sibling packages whether it's imported as ``dashboard.queries``
# (from the chat app or from tests) or as ``queries`` (from the Streamlit
# entrypoint). Idempotent — safe to call twice.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rag.history import _get_connection  # noqa: E402
from rag.topics import _TOPICS  # noqa: E402


# ---------------------------------------------------------------------------
# Topic keyword mapping (v1 heuristic)
# ---------------------------------------------------------------------------

# Lowercase keywords per unit. A single query can match multiple units on
# purpose: the v1 assignment is approximate and is shown with a disclaimer.
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "I": [
        "introducción",
        "física",
        "medición",
        "unidades",
        "escalar",
        "vector",
        "magnitud",
        "sistema internacional",
        "unidades de medida",
    ],
    "II": [
        "cinemática",
        "una dimensión",
        "rectilíneo",
        "velocidad",
        "aceleración",
        "posición",
        "tiempo",
        "mru",
        "mruv",
        "movimiento uniforme",
        "movimiento acelerado",
    ],
    "III": [
        "cinemática en dos",
        "cinemática en tres",
        "dos dimensiones",
        "tres dimensiones",
        "proyectil",
        "tiro oblicuo",
        "tiro horizontal",
        "velocidad relativa",
        "movimiento parabólico",
    ],
    "IV": [
        "newton",
        "leyes de newton",
        "fuerza",
        "masa",
        "inercia",
        "dinámica",
        "acción y reacción",
        "normal",
        "rozamiento",
        "tensión",
    ],
    "V": [
        "trabajo",
        "energía",
        "cinética",
        "potencial",
        "potencia",
        "conservación de la energía",
        "energía mecánica",
        "fuerza conservativa",
    ],
    "VI": [
        "circular",
        "centrípeta",
        "angular",
        "cinemática circular",
        "dinámica circular",
        "movimiento circular",
        "velocidad angular",
        "aceleración centrípeta",
    ],
    "VII": [
        "fluidos",
        "estática de fluidos",
        "presión",
        "hidrostática",
        "arquímedes",
        "principio de arquímedes",
        "empuje",
    ],
    "VIII": [
        "dinámica de fluidos",
        "bernoulli",
        "hidrodinámica",
        "viscosidad",
        "flujo",
        "ecuación de continuidad",
        " Reynolds",
    ],
    "IX": [
        "partículas",
        "momento lineal",
        "conservación del momento",
        "choque",
        "colisión",
        "impulso",
        "sistema de partículas",
        "centro de masa",
    ],
    "X": [
        "cuerpo rígido",
        "rotación del cuerpo rígido",
        "torque",
        "momento de inercia",
        "momento angular",
        "rígido",
        "rotación",
    ],
    "XI": [
        "oscilatorio",
        "oscilaciones",
        "muelle",
        "péndulo",
        "armónico",
        "frecuencia",
        "período",
        "movimiento armónico simple",
        "masa resorte",
    ],
    "XII": [
        "ondulatorio",
        "ondas",
        "sonido",
        "interferencia",
        "longitud de onda",
        "frecuencia",
        "propagación",
        "ondas mecánicas",
    ],
}


def _topic_match_score(topic_number: str, text: str) -> bool:
    """Return True when ``text`` contains any keyword of the given topic."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in _TOPIC_KEYWORDS[topic_number])


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

_TIME_WINDOWS = {
    "todo": None,
    "última semana": timedelta(days=7),
    "últimas 24h": timedelta(days=1),
}


def _window_to_iso_cutoff(window_label: str) -> str | None:
    """Convert a dashboard time-window label to an ISO 8601 cutoff string."""
    delta = _TIME_WINDOWS.get(window_label)
    if delta is None:
        return None
    cutoff = datetime.now(timezone.utc) - delta
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp produced by ``rag.history``.

    Falls back to replacing the trailing ``Z`` with ``+00:00`` when the
    strict parser rejects the legacy format.
    """
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _relative_time(value: str) -> str:
    """Return a human-friendly Spanish relative time for a UTC ISO timestamp."""
    try:
        then = _parse_iso_timestamp(value)
    except (ValueError, TypeError):
        return "desconocido"

    now = datetime.now(timezone.utc)
    diff = now - then

    if diff.total_seconds() < 60:
        return "hace un momento"
    if diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() // 60)
        return f"hace {minutes}m"
    if diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() // 3600)
        return f"hace {hours}h"
    days = diff.days
    if days < 30:
        return f"hace {days}d"
    if days < 365:
        months = days // 30
        return f"hace {months}m"
    years = days // 365
    return f"hace {years}a"


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def _user_messages_where_clause(window_label: str | None = None) -> tuple[str, tuple]:
    """Build the WHERE clause for user messages with optional time filter."""
    cutoff = _window_to_iso_cutoff(window_label) if window_label else None
    if cutoff:
        return "WHERE role = 'user' AND created_at >= ?", (cutoff,)
    return "WHERE role = 'user'", ()


def get_kpis() -> dict:
    """Return the three header KPIs for the dashboard.

    Returns a dict with keys ``total_queries``, ``unique_students`` and
    ``last_activity`` (relative string or ``"nunca"``). No student names or
    ids are included.
    """
    conn = _get_connection()
    where, params = _user_messages_where_clause()

    total_row = conn.execute(
        f"SELECT COUNT(*) FROM messages {where}",
        params,
    ).fetchone()
    total_queries = total_row[0] if total_row else 0

    unique_row = conn.execute(
        f"SELECT COUNT(DISTINCT student_id) FROM messages {where}",
        params,
    ).fetchone()
    unique_students = unique_row[0] if unique_row else 0

    last_row = conn.execute(
        f"SELECT MAX(created_at) FROM messages {where}",
        params,
    ).fetchone()
    last_activity = _relative_time(last_row[0]) if last_row and last_row[0] else "nunca"

    return {
        "total_queries": total_queries,
        "unique_students": unique_students,
        "last_activity": last_activity,
    }


def get_top_queries(window_label: str | None = None, limit: int = 20) -> list[dict]:
    """Return the most frequent user queries grouped by exact content.

    Each element has keys ``content``, ``count`` and ``last_seen`` (relative
    time string). The result is ordered by count descending and then by the
    most recent occurrence descending.
    """
    conn = _get_connection()
    where, params = _user_messages_where_clause(window_label)
    params = params + (limit,)

    cursor = conn.execute(
        f"""
        SELECT content, COUNT(*) AS cnt, MAX(created_at) AS last
        FROM messages
        {where}
        GROUP BY content
        ORDER BY cnt DESC, last DESC
        LIMIT ?
        """,
        params,
    )
    rows = cursor.fetchall()

    return [
        {
            "content": row[0],
            "count": row[1],
            "last_seen": _relative_time(row[2]),
        }
        for row in rows
    ]


def get_recent_queries(limit: int = 10) -> list[dict]:
    """Return the most recent user queries without any identifier.

    Each element has keys ``content`` and ``when`` (relative time string).
    """
    conn = _get_connection()
    cursor = conn.execute(
        """
        SELECT content, created_at
        FROM messages
        WHERE role = 'user'
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()

    return [
        {
            "content": row[0],
            "when": _relative_time(row[1]),
        }
        for row in rows
    ]


def get_topic_counts() -> List[dict]:
    """Return approximate query counts per syllabus unit.

    The mapping is keyword-based and intentionally noisy. The UI must show
    a disclaimer next to the chart. No student identifiers are exposed.

    Each element has keys ``number``, ``title`` and ``count``.
    """
    conn = _get_connection()
    cursor = conn.execute(
        """
        SELECT content
        FROM messages
        WHERE role = 'user'
        """
    )
    contents = [row[0] for row in cursor.fetchall()]

    counts: dict[str, int] = {topic["numero"]: 0 for topic in _TOPICS}
    for text in contents:
        for topic in _TOPICS:
            number = topic["numero"]
            if _topic_match_score(number, text):
                counts[number] += 1

    return [
        {
            "number": topic["numero"],
            "title": topic["titulo"],
            "count": counts[topic["numero"]],
        }
        for topic in _TOPICS
    ]


def get_available_time_windows() -> list[str]:
    """Return the time-window labels supported by the dashboard filters."""
    return list(_TIME_WINDOWS.keys())

"""Streamlit dashboard for professors (v1).

Shows anonymous aggregates of student questions so professors can identify
which topics need reinforcement. No student names or ids are displayed.
"""

from __future__ import annotations

import base64
from pathlib import Path
import sys

# Streamlit runs this file with cwd set to ``dashboard/``, which makes
# ``dashboard`` invisible as a package and the import of ``rag.history``
# below would also fail without ``repo_root`` on ``sys.path``. Adding the
# repo root here lets both ``from dashboard.queries import ...`` and the
# deeper ``from rag...`` resolve, whether this file is run as the
# Streamlit entrypoint or imported by a test. Idempotent.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

_DASHBOARD_DIR = Path(__file__).resolve().parent
_CSS = _DASHBOARD_DIR / "static" / "faradai.css"
_LOGO = _DASHBOARD_DIR / "static" / "img" / "logo-wordmark.svg"
_LOGO_INLINE = _LOGO.read_text()  # SVG completo como string, embebido en HTML

import streamlit as st

from dashboard.queries import (
    get_available_time_windows,
    get_kpis,
    get_recent_queries,
    get_topic_counts,
    get_top_queries,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shorten_topic_title(title: str, max_length: int = 35) -> str:
    """Return a chart-friendly topic label, truncated if too long."""
    if len(title) <= max_length:
        return title
    return title[: max_length - 3] + "..."




# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Asistente de Física — Panel de profesores",
    page_icon="📊",
    layout="wide",
)

# Header: the wordmark SVG is embedded inline (not via base64 src) so the
# F-mark at the start of the SVG renders alongside the "FaradAI" text in
# the same container. Width is set to ~280px so the F is visibly prominent.
st.markdown(
    f"""
    <div class="dashboard-header">
      <div class="dashboard-logo">{_LOGO_INLINE}</div>
      <div class="dashboard-header-text">
        <div class="dashboard-subtitle">Panel de profesores — Asistente de Física 1</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")
st.caption(
    "Panel de métricas anónimas para reforzar los contenidos que más necesitan los estudiantes. "
    "Versión abierta durante la semana de pruebas."
)


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

st.sidebar.header("Filtros")
selected_window = st.sidebar.selectbox(
    "Período",
    options=get_available_time_windows(),
    index=0,
    help="Restringe los widgets de arriba al período seleccionado. Las últimas consultas siempre muestran todo el historial.",
)


# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------

kpis = get_kpis()

col_total, col_students, col_last = st.columns(3)
with col_total:
    st.metric(label="Total de consultas", value=kpis["total_queries"])
with col_students:
    st.metric(label="Estudiantes únicos", value=kpis["unique_students"])
with col_last:
    st.metric(label="Última actividad", value=kpis["last_activity"])


# ---------------------------------------------------------------------------
# Widget 1: top queries
# ---------------------------------------------------------------------------

st.subheader("🔥 Consultas más frecuentes")

top_queries = get_top_queries(window_label=selected_window, limit=20)
if not top_queries:
    st.info(
        "Todavía no hay consultas registradas para este período. "
        "Cuando los estudiantes empiecen a chatear, verás aquí lo que más se pregunta."
    )
else:
    rows = []
    for item in top_queries:
        content = item["content"]
        if len(content) > 120:
            content = content[:117] + "..."
        rows.append(
            {
                "consulta": content,
                "count": item["count"],
                "última vez": item["last_seen"],
            }
        )
    st.dataframe(
        rows,
        column_config={
            "consulta": st.column_config.TextColumn("Consulta", width="large"),
            "count": st.column_config.NumberColumn("Veces", format="%d"),
            "última vez": st.column_config.TextColumn("Última vez"),
        },
        width='stretch',
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Widget 2: topic bar chart
# ---------------------------------------------------------------------------

st.subheader("📚 Consultas por unidad temática")

topic_counts = get_topic_counts()
has_any_topic_match = any(item["count"] > 0 for item in topic_counts)

if not has_any_topic_match:
    st.info(
        "Todavía no hay suficientes consultas para hacer una asignación temática aproximada. "
        "Este gráfico se activará automáticamente cuando lleguen más preguntas."
    )
else:
    st.warning(
        "Asignación aproximada basada en palabras clave — puede no reflejar el contenido real de la consulta.",
        icon="⚠️",
    )

    chart_data = {
        _shorten_topic_title(item["title"]): item["count"]
        for item in topic_counts
    }
    st.bar_chart(
        chart_data,
        width='stretch',
        horizontal=False,
        color="#ABDDC4",  # --color-brand-primary-soft
    )


# ---------------------------------------------------------------------------
# Widget 3: recent queries
# ---------------------------------------------------------------------------

st.subheader("🕐 Últimas consultas")

recent = get_recent_queries(limit=10)
if not recent:
    st.info(
        "Aún no llegaron consultas. Vuelve más tarde para ver las últimas preguntas de los estudiantes."
    )
else:
    rows = [
        {
            "consulta": item["content"],
            "cuándo": item["when"],
        }
        for item in recent
    ]
    st.dataframe(
        rows,
        column_config={
            "consulta": st.column_config.TextColumn("Consulta", width="large"),
            "cuándo": st.column_config.TextColumn("Cuándo"),
        },
        width='stretch',
        hide_index=True,
    )

st.markdown(
    '<div class="dashboard-footnote">'
    'Anonimato: ninguna consulta está asociada a un estudiante. '
    'Las preguntas se cuentan por contenido exacto; si dos estudiantes preguntaron '
    'lo mismo, cuentan como dos consultas con la misma intención.'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# FaradAI brand injection
# ---------------------------------------------------------------------------

if _CSS.exists():
    st.markdown(f"<style>{_CSS.read_text()}</style>", unsafe_allow_html=True)

"""Entry point for Hugging Face Spaces Streamlit SDK.

HF Spaces ejecuta este archivo como entrypoint cuando el Space usa el SDK
nativo "Streamlit" (alternativa gratuita al Docker SDK, que requiere
plan PRO para Spaces nuevos). El código real del dashboard vive en
``dashboard/app.py`` para mantener el resto del repo organizado.
Este wrapper solo delega.

Como Streamlit SDK no acepta un subdirectorio como entrypoint (``app.py``
debe estar en la raíz del repo del Space), usamos ``runpy.run_path`` para
ejecutar ``dashboard/app.py`` en el contexto del script principal. Esto
preserva ``__name__ == '__main__'`` y deja que ``Path(__file__).parent`` se
resuelva correctamente dentro de ``dashboard/app.py``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so that ``from dashboard.queries
# import ...`` inside the wrapped script resolves. Idempotent.
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Hand off to the real Streamlit entrypoint. run_name keeps the script
# behaving as if it had been invoked directly (Streamlit inspects the
# module name internally to set up routing).
runpy.run_path(str(_REPO_ROOT / "dashboard" / "app.py"), run_name="__main__")

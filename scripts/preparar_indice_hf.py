"""Ensure the HuggingFace embedding model is available locally.

Idempotent script that ensures `intfloat/multilingual-e5-small` is available
locally under `rag/index/hf-model/`. It uses `SentenceTransformer` first-load
with `SENTENCE_TRANSFORMERS_HOME` and `HF_HOME` pointing to the same directory,
so sentence-transformers downloads exactly the files it needs (no duplicate
onnx/openvino/pytorch copies).

Used in two places:
- Dev: a fresh clone runs this script to populate the local model dir
  before running the app or re-baking the chroma index.
- Deploy: the Dockerfile invokes this same script in its build step
  (baking the model into the image), so HF Spaces' free tier 100 MB
  LFS cap does not block the push (the model is 448 MB).

Notes:
- The 5-PDF canonical corpus is enforced by `scripts/indexar_pdfs.py`;
  this script only prepares the embedding model, not the corpus.
- marker-pdf/surya models are baked at Docker build time via
  `create_model_dict()` and `MODEL_CACHE_DIR` (see Dockerfile).
- ChromaDB paths: dev uses `data/chroma/` (default `CHROMA_PERSIST_DIR`),
  deploy uses `rag/index/chroma/` (set in Dockerfile).

Usage:
    python scripts/preparar_indice_hf.py

Env:
    SENTENCE_TRANSFORMERS_HOME / HF_HOME (optional): override cache dir.
"""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
DEFAULT_HOME = Path(__file__).resolve().parent.parent / "rag" / "index" / "hf-model"


def _find_snapshot(home: Path) -> Path | None:
    """Return the snapshot dir if the model is already cached, else None."""
    repo_dir = home / f"models--{MODEL_NAME.replace('/', '--')}"
    snapshots_dir = repo_dir / "snapshots"
    if not snapshots_dir.exists():
        return None
    for snapshot in snapshots_dir.iterdir():
        if snapshot.is_dir() and (snapshot / "config.json").exists():
            return snapshot
    return None


def ensure_model(home: Path | str | None = None) -> Path:
    """Download the model if missing; return the local snapshot directory."""
    target = Path(home or os.getenv("HF_HOME") or DEFAULT_HOME)
    target.mkdir(parents=True, exist_ok=True)

    # Point both libraries to the same tree so the bake is consistent.
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(target)
    os.environ["HF_HOME"] = str(target)

    existing = _find_snapshot(target)
    if existing:
        print(f"[HF] {MODEL_NAME} already present at {existing}, skipping download.")
        return existing

    print(f"[HF] Downloading {MODEL_NAME} to {target} ...")
    SentenceTransformer(MODEL_NAME)
    snapshot = _find_snapshot(target)
    if snapshot is None:
        raise RuntimeError("Model download finished but snapshot was not found.")
    print(f"[HF] Model ready at {snapshot}")
    return snapshot


if __name__ == "__main__":
    ensure_model()

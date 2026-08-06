"""Post-bake assertion for LaTeX formula richness.

Connects to ChromaDB, counts inline ($...$) and display ($$...$$) formula
delimiters across all indexed chunks, and asserts the NFR from the
marker-pdf-loader spec: ≥ 2000 total LaTeX occurrences across the 5-PDF
canonical corpus.

Usage:
    python scripts/verify_latex.py
    CHROMA_PERSIST_DIR=./data/chroma python scripts/verify_latex.py
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.retrievers import VectorStore  # noqa: E402

DEFAULT_MIN_TOTAL = 2000
DEFAULT_PERSIST_DIR = "./data/chroma"


def count_latex(text: str) -> tuple[int, int]:
    """Return (display_count, inline_count) for a single document.

    Display formulas are $$...$$ blocks. Inline formulas are $...$ pairs
    that are not part of a $$ block.
    """
    # Count display formulas first so they are not double-counted as inline.
    display = len(re.findall(r"\$\$(.*?)\$\$", text, re.DOTALL))
    # Strip display blocks before counting inline formulas.
    text_without_display = re.sub(r"\$\$(.*?)\$\$", "", text, flags=re.DOTALL)
    inline = len(re.findall(r"\$([^$\n]+?)\$", text_without_display))
    return display, inline


def verify_latex(persist_dir: str | None = None, min_total: int = DEFAULT_MIN_TOTAL) -> int:
    """Count LaTeX occurrences in the baked index and assert the NFR.

    Args:
        persist_dir: ChromaDB persist directory. Defaults to CHROMA_PERSIST_DIR
            env var or ./data/chroma.
        min_total: Minimum required total LaTeX occurrences.

    Returns:
        0 if the assertion passes, 1 otherwise.
    """
    persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", DEFAULT_PERSIST_DIR)
    vector_store = VectorStore(persist_dir=persist_dir)
    count = vector_store.count()

    if count == 0:
        print(f"[FAIL] Collection at {persist_dir} is empty (0 chunks).")
        return 1

    print(f"[INFO] Checking {count} chunks at {persist_dir}...")

    collection_data = vector_store.collection.get(include=["documents", "metadatas"])
    documents = collection_data.get("documents") or []
    metadatas = collection_data.get("metadatas") or []

    per_doc: dict[str, dict[str, int]] = defaultdict(lambda: {"display": 0, "inline": 0, "total": 0})
    total_display = 0
    total_inline = 0

    for text, meta in zip(documents, metadatas):
        source = Path(meta.get("source", "unknown")).name
        display, inline = count_latex(text)
        total = display + inline
        per_doc[source]["display"] += display
        per_doc[source]["inline"] += inline
        per_doc[source]["total"] += total
        total_display += display
        total_inline += inline

    total = total_display + total_inline

    print()
    print("=" * 60)
    print("LaTeX formula counts by source:")
    print("=" * 60)
    for source in sorted(per_doc.keys()):
        stats = per_doc[source]
        print(
            f"  {source}: "
            f"display={stats['display']}, inline={stats['inline']}, total={stats['total']}"
        )
    print("-" * 60)
    print(f"  TOTAL: display={total_display}, inline={total_inline}, sum={total}")
    print(f"  REQUIRED: ≥ {min_total}")
    print("=" * 60)

    if total < min_total:
        print()
        print("[FAIL] LaTeX assertion failed.")
        top5 = sorted(per_doc.items(), key=lambda kv: kv[1]["total"], reverse=True)[:5]
        print("Top 5 sources by formula count:")
        for source, stats in top5:
            print(
                f"  {source}: display={stats['display']}, "
                f"inline={stats['inline']}, total={stats['total']}"
            )
        return 1

    print()
    print(f"[PASS] LaTeX assertion passed ({total} ≥ {min_total}).")
    return 0


if __name__ == "__main__":
    sys.exit(verify_latex())

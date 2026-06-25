"""Indexa los PDFs de data/pdfs/ en ChromaDB.

Idempotente: si corrés dos veces, no duplica. Detecta PDFs ya
indexados por nombre de archivo y los salta.

Uso:
    python scripts/indexar_pdfs.py              # indexa todos los PDFs
    python scripts/indexar_pdfs.py --reset      # borra el store y re-indexa
    python scripts/indexar_pdfs.py --pdf path   # indexa un PDF específico
"""

import argparse
import sys
import time
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.loaders import load_pdfs  # noqa: E402
from rag.retrievers import EmbeddingsModel, VectorStore  # noqa: E402
from rag.splitters import split_documents  # noqa: E402

DEFAULT_PDFS_DIR = PROJECT_ROOT / "data" / "pdfs"


def index_pdfs(
    pdf_paths: list[Path],
    vector_store: VectorStore,
    embeddings: EmbeddingsModel,
) -> dict:
    """Indexa una lista de PDFs. Devuelve estadísticas."""
    stats = {"pdfs": 0, "chunks": 0, "skipped": 0, "errors": []}

    indexed_sources = {meta["source"] for meta in vector_store.collection.get()["metadatas"] or []}

    for pdf in pdf_paths:
        if str(pdf) in indexed_sources:
            print(f"  [SKIP] {pdf.name} (ya indexado)")
            stats["skipped"] += 1
            continue

        print(f"  [LOAD] {pdf.name}...")
        try:
            t0 = time.time()
            docs = load_pdfs([pdf])
            t_load = time.time() - t0
        except Exception as e:
            print(f"  [ERROR] {pdf.name}: {e}")
            stats["errors"].append((pdf.name, str(e)))
            continue

        print(f"  [SPLIT] {pdf.name} ({len(docs)} docs -> chunks)...")
        t0 = time.time()
        chunks = split_documents(docs)
        # Agregar chunk_index a la metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
        t_split = time.time() - t0

        if not chunks:
            print(f"  [WARN] {pdf.name}: sin chunks, salteando")
            continue

        print(f"  [EMBED] {pdf.name} ({len(chunks)} chunks)...")
        t0 = time.time()
        texts = [c.page_content for c in chunks]
        vectors = embeddings.embed_documents(texts)
        t_embed = time.time() - t0

        print(f"  [STORE] {pdf.name}...")
        t0 = time.time()
        vector_store.add_documents(chunks, vectors)
        t_store = time.time() - t0

        print(
            f"  [DONE] {pdf.name}: {len(chunks)} chunks | "
            f"load={t_load:.1f}s split={t_split:.2f}s "
            f"embed={t_embed:.1f}s store={t_store:.2f}s"
        )
        stats["pdfs"] += 1
        stats["chunks"] += len(chunks)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexa PDFs en ChromaDB")
    parser.add_argument(
        "--pdfs-dir",
        type=Path,
        default=DEFAULT_PDFS_DIR,
        help="Directorio con PDFs (default: data/pdfs/)",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Indexa un PDF específico en vez de todo el directorio",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra el store y re-indexa desde cero",
    )
    args = parser.parse_args()

    if args.reset:
        print("[RESET] Borrando vector store...")
        VectorStore().wipe_disk()

    if args.pdf:
        if not args.pdf.exists():
            print(f"[ERROR] PDF no encontrado: {args.pdf}")
            return 1
        pdfs = [args.pdf]
    else:
        if not args.pdfs_dir.exists():
            print(f"[ERROR] Directorio no encontrado: {args.pdfs_dir}")
            return 1
        pdfs = sorted(args.pdfs_dir.glob("*.pdf"))
        if not pdfs:
            print(f"[WARN] No hay PDFs en {args.pdfs_dir}")
            return 0

    print(f"[INIT] Cargando modelo de embeddings (MPS si está disponible)...")
    embeddings = EmbeddingsModel()
    print(f"[INIT] Device: {embeddings.device}")

    vector_store = VectorStore()
    print(f"[INIT] Vector store: {vector_store.persist_dir} (collection={vector_store.collection_name})")
    print(f"[INIT] PDFs en store: {vector_store.count()}")
    print()

    print(f"[INDEX] Procesando {len(pdfs)} PDF(s)...")
    stats = index_pdfs(pdfs, vector_store, embeddings)

    print()
    print("=" * 60)
    print(f"  PDFs indexados: {stats['pdfs']}")
    print(f"  PDFs saltados (ya indexados): {stats['skipped']}")
    print(f"  Total chunks nuevos: {stats['chunks']}")
    print(f"  Errores: {len(stats['errors'])}")
    print(f"  Total en store: {vector_store.count()}")
    print("=" * 60)

    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())

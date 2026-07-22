"""Indexa PDFs de data/pdfs/ y markdown de data/markdown/ en ChromaDB.

Idempotente: si corrés dos veces, no duplica. Detecta archivos ya
indexados por ruta absoluta y los salta.

Uso:
    python scripts/indexar_pdfs.py              # indexa PDFs + .md
    python scripts/indexar_pdfs.py --reset      # borra el store y re-indexa
    python scripts/indexar_pdfs.py --pdf path   # indexa un PDF específico
    python scripts/indexar_pdfs.py --md path    # indexa un .md específico
"""

import argparse
import sys
import time
from pathlib import Path

from langchain_community.document_loaders import TextLoader

# Asegurar que el root del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.loaders import load_pdfs  # noqa: E402
from rag.retrievers import EmbeddingsModel, VectorStore  # noqa: E402
from rag.splitters import split_documents  # noqa: E402

DEFAULT_PDFS_DIR = PROJECT_ROOT / "data" / "pdfs"
DEFAULT_MARKDOWN_DIR = PROJECT_ROOT / "data" / "markdown"


def load_markdown(md_paths: list[Path]) -> list:
    """Carga archivos markdown como Documents (uno por archivo).

    Wrapper sobre TextLoader de langchain_community. Para el caso del
    prototipo (un puñado de .md curados a mano), la chunkificación por
    RecursiveCharacterTextSplitter maneja bien la estructura de secciones.
    """
    documents = []
    for path in md_paths:
        loader = TextLoader(str(path), encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = str(path)
        documents.extend(docs)
    return documents


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


def index_markdown(
    md_paths: list[Path],
    vector_store: VectorStore,
    embeddings: EmbeddingsModel,
) -> dict:
    """Indexa una lista de archivos markdown. Devuelve estadísticas."""
    stats = {"markdown": 0, "chunks": 0, "skipped": 0, "errors": []}

    indexed_sources = {meta["source"] for meta in vector_store.collection.get()["metadatas"] or []}

    for md in md_paths:
        if str(md) in indexed_sources:
            print(f"  [SKIP] {md.name} (ya indexado)")
            stats["skipped"] += 1
            continue

        print(f"  [LOAD] {md.name}...")
        try:
            t0 = time.time()
            docs = load_markdown([md])
            t_load = time.time() - t0
        except Exception as e:
            print(f"  [ERROR] {md.name}: {e}")
            stats["errors"].append((md.name, str(e)))
            continue

        print(f"  [SPLIT] {md.name} ({len(docs)} docs -> chunks)...")
        t0 = time.time()
        chunks = split_documents(docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
        t_split = time.time() - t0

        if not chunks:
            print(f"  [WARN] {md.name}: sin chunks, salteando")
            continue

        print(f"  [EMBED] {md.name} ({len(chunks)} chunks)...")
        t0 = time.time()
        texts = [c.page_content for c in chunks]
        vectors = embeddings.embed_documents(texts)
        t_embed = time.time() - t0

        print(f"  [STORE] {md.name}...")
        t0 = time.time()
        vector_store.add_documents(chunks, vectors)
        t_store = time.time() - t0

        print(
            f"  [DONE] {md.name}: {len(chunks)} chunks | "
            f"load={t_load:.1f}s split={t_split:.2f}s "
            f"embed={t_embed:.1f}s store={t_store:.2f}s"
        )
        stats["markdown"] += 1
        stats["chunks"] += len(chunks)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexa PDFs y markdown en ChromaDB")
    parser.add_argument(
        "--pdfs-dir",
        type=Path,
        default=DEFAULT_PDFS_DIR,
        help="Directorio con PDFs (default: data/pdfs/)",
    )
    parser.add_argument(
        "--markdown-dir",
        type=Path,
        default=DEFAULT_MARKDOWN_DIR,
        help="Directorio con .md (default: data/markdown/)",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="Indexa un PDF específico en vez de todo el directorio",
    )
    parser.add_argument(
        "--md",
        type=Path,
        help="Indexa un .md específico en vez de todo el directorio",
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

    # Recolectar PDFs
    if args.pdf:
        if not args.pdf.exists():
            print(f"[ERROR] PDF no encontrado: {args.pdf}")
            return 1
        pdfs = [args.pdf]
    else:
        if not args.pdfs_dir.exists():
            print(f"[WARN] Directorio de PDFs no encontrado: {args.pdfs_dir}")
            pdfs = []
        else:
            pdfs = sorted(args.pdfs_dir.glob("*.pdf"))

    # Recolectar markdown
    if args.md:
        if not args.md.exists():
            print(f"[ERROR] Markdown no encontrado: {args.md}")
            return 1
        markdowns = [args.md]
    else:
        if not args.markdown_dir.exists():
            print(f"[WARN] Directorio de markdown no encontrado: {args.markdown_dir}")
            markdowns = []
        else:
            markdowns = sorted(args.markdown_dir.glob("*.md"))

    if not pdfs and not markdowns:
        print("[WARN] No hay PDFs ni markdown para indexar")
        return 0

    print(f"[INIT] Cargando modelo de embeddings (MPS si está disponible)...")
    embeddings = EmbeddingsModel()
    print(f"[INIT] Device: {embeddings.device}")

    vector_store = VectorStore()
    print(f"[INIT] Vector store: {vector_store.persist_dir} (collection={vector_store.collection_name})")
    print(f"[INIT] Documentos en store: {vector_store.count()}")
    print()

    total_errors = []
    pdf_stats = {"indexed": 0, "chunks": 0, "skipped": 0}
    md_stats = {"indexed": 0, "chunks": 0, "skipped": 0}

    if pdfs:
        print(f"[INDEX] Procesando {len(pdfs)} PDF(s)...")
        s = index_pdfs(pdfs, vector_store, embeddings)
        pdf_stats = {"indexed": s["pdfs"], "chunks": s["chunks"], "skipped": s["skipped"]}
        total_errors.extend(s["errors"])

    if markdowns:
        print(f"[INDEX] Procesando {len(markdowns)} markdown(s)...")
        s = index_markdown(markdowns, vector_store, embeddings)
        md_stats = {"indexed": s["markdown"], "chunks": s["chunks"], "skipped": s["skipped"]}
        total_errors.extend(s["errors"])

    print()
    print("=" * 60)
    print(f"  PDFs indexados: {pdf_stats['indexed']} (saltados: {pdf_stats['skipped']}, chunks: {pdf_stats['chunks']})")
    print(f"  Markdown indexados: {md_stats['indexed']} (saltados: {md_stats['skipped']}, chunks: {md_stats['chunks']})")
    print(f"  Total en store: {vector_store.count()}")
    print(f"  Errores: {len(total_errors)}")
    print("=" * 60)

    return 0 if not total_errors else 1


if __name__ == "__main__":
    sys.exit(main())

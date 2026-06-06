"""
ingest.py — Document Ingestion Pipeline
Loads PDFs, TXT, and MD files from the data/ folder,
splits them into chunks, and indexes them into ChromaDB via rag.py.
"""

import os
import uuid
import argparse
from pathlib import Path

from pypdf import PdfReader
from rag import add_documents, clear_collection, get_document_count

# ── Configuration ──────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 100    # overlap between consecutive chunks


# ── Text Extraction ────────────────────────────────────────────────────────────

def extract_text_from_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def extract_text_from_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".txt", ".md"):
        return extract_text_from_txt(filepath)
    else:
        print(f"[INGEST] Skipping unsupported file: {filepath}")
        return ""


# ── Chunking ───────────────────────────────────────────────────────────────────

def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ── Main Ingestion ─────────────────────────────────────────────────────────────

def ingest_file(filepath: str) -> int:
    filename = Path(filepath).name
    print(f"[INGEST] Processing: {filename}")

    text = extract_text(filepath)
    if not text.strip():
        print(f"[INGEST] No text found in: {filename}")
        return 0

    raw_chunks = split_text(text)
    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        chunks.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{filepath}-{i}")),
            "text": chunk_text,
            "metadata": {
                "source": filename,
                "filepath": filepath,
                "chunk_index": i,
            },
        })

    add_documents(chunks)
    print(f"[INGEST] ✅ {filename} → {len(chunks)} chunks indexed.")
    return len(chunks)


def ingest_all(data_dir: str = DATA_DIR, reset: bool = False):
    if reset:
        print("[INGEST] Clearing existing collection...")
        clear_collection()

    supported = (".pdf", ".txt", ".md")
    files = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if Path(f).suffix.lower() in supported
    ]

    if not files:
        print(f"[INGEST] No supported files found in: {data_dir}")
        return

    total_chunks = 0
    for filepath in files:
        total_chunks += ingest_file(filepath)

    print(f"\n[INGEST] Done! Total chunks in DB: {get_document_count()}")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB")
    parser.add_argument("--data-dir", default=DATA_DIR, help="Directory containing documents")
    parser.add_argument("--reset", action="store_true", help="Clear existing collection before ingesting")
    parser.add_argument("--file", default=None, help="Ingest a single file")
    args = parser.parse_args()

    if args.file:
        ingest_file(args.file)
    else:
        ingest_all(data_dir=args.data_dir, reset=args.reset)

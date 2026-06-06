"""
rag.py — Retrieval-Augmented Generation Engine
Uses ChromaDB as the vector store and sentence-transformers for embeddings.
"""

import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── Configuration ──────────────────────────────────────────────────────────────
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "rag_documents"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # fast, lightweight, runs offline
TOP_K = 5                                # number of chunks to retrieve

# ── Singleton instances ────────────────────────────────────────────────────────
_embedder = None
_collection = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        print("[RAG] Loading embedding model...")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Public API ─────────────────────────────────────────────────────────────────

def add_documents(chunks: list[dict]):
    """
    Add text chunks to the vector store.

    Each chunk must be a dict with:
      - 'id'       : unique string ID
      - 'text'     : the chunk content
      - 'metadata' : dict with source info (filename, page, etc.)
    """
    collection = _get_collection()
    embedder = _get_embedder()

    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()
    ids = [c["id"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    print(f"[RAG] Indexed {len(chunks)} chunks.")


def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve the most relevant chunks for a given query.

    Returns a list of dicts with keys: text, metadata, distance.
    """
    collection = _get_collection()
    embedder = _get_embedder()

    query_embedding = embedder.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({"text": doc, "metadata": meta, "distance": dist})
    return hits


def build_context(query: str) -> tuple[str, list[dict]]:
    """
    Retrieve relevant chunks and format them into a context string.

    Returns (context_string, list_of_sources).
    """
    hits = retrieve(query)
    if not hits:
        return "", []

    context_parts = []
    sources = []
    for i, hit in enumerate(hits, 1):
        context_parts.append(f"[Source {i}]\n{hit['text']}")
        sources.append(hit["metadata"])

    return "\n\n".join(context_parts), sources


def get_document_count() -> int:
    """Return the number of indexed chunks."""
    try:
        return _get_collection().count()
    except Exception:
        return 0


def clear_collection():
    """Delete all documents from the vector store."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    client.delete_collection(COLLECTION_NAME)
    global _collection
    _collection = None
    print("[RAG] Collection cleared.")

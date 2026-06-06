"""
chatbot.py — Ollama LLM Integration
Sends the user query + retrieved RAG context to a local Ollama model
and returns the response (streaming supported).
"""

import ollama
from rag import build_context, get_document_count

# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_MODEL = "llama3"   # Change to mistral, phi3, gemma, etc.

SYSTEM_PROMPT = """You are a helpful AI assistant. You answer questions based on the provided context documents.

Rules:
- If the context contains relevant information, use it to answer accurately.
- If the context does not contain enough information, say so clearly and answer from your general knowledge if possible.
- Keep answers concise, clear, and well-structured.
- Cite sources when referring to specific document content.
- Never make up facts.
"""


# ── Chat Function ──────────────────────────────────────────────────────────────

def chat(query: str, model: str = DEFAULT_MODEL, use_rag: bool = True) -> dict:
    """
    Send a query to Ollama, optionally augmented with RAG context.

    Returns:
        {
            "answer": str,
            "sources": list[dict],
            "model": str,
            "used_rag": bool,
        }
    """
    context = ""
    sources = []

    if use_rag and get_document_count() > 0:
        context, sources = build_context(query)

    # Build the user message
    if context:
        user_message = f"""Context from your documents:
---
{context}
---

Question: {query}"""
    else:
        user_message = query

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    response = ollama.chat(
        model=model,
        messages=messages,
    )

    answer = response["message"]["content"]

    return {
        "answer": answer,
        "sources": sources,
        "model": model,
        "used_rag": bool(context),
    }


def stream_chat(query: str, model: str = DEFAULT_MODEL, use_rag: bool = True):
    """
    Generator that streams the response token by token.

    Yields chunks of text as they arrive from Ollama.
    First yields a special JSON header with sources info.
    """
    context = ""
    sources = []

    if use_rag and get_document_count() > 0:
        context, sources = build_context(query)

    if context:
        user_message = f"""Context from your documents:
---
{context}
---

Question: {query}"""
    else:
        user_message = query

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    stream = ollama.chat(
        model=model,
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        token = chunk["message"]["content"]
        if token:
            yield token


def list_models() -> list[str]:
    """Return list of locally available Ollama models."""
    try:
        result = ollama.list()
        return [m["name"] for m in result.get("models", [])]
    except Exception:
        return [DEFAULT_MODEL]

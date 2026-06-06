"""
app.py — Flask Web Application
Serves the chat UI and exposes REST API endpoints.
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename

from chatbot import chat, stream_chat, list_models, DEFAULT_MODEL
from ingest import ingest_file, ingest_all
from rag import get_document_count, clear_collection

# ── App Setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024   # 50 MB upload limit
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "data")

ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "chroma_db"), exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    doc_count = get_document_count()
    models = list_models()
    return render_template("index.html", doc_count=doc_count, models=models, default_model=DEFAULT_MODEL)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Non-streaming chat endpoint."""
    data = request.get_json()
    query = (data or {}).get("query", "").strip()
    model = (data or {}).get("model", DEFAULT_MODEL)
    use_rag = (data or {}).get("use_rag", True)

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        result = chat(query, model=model, use_rag=use_rag)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """Streaming chat endpoint using Server-Sent Events."""
    data = request.get_json()
    query = (data or {}).get("query", "").strip()
    model = (data or {}).get("model", DEFAULT_MODEL)
    use_rag = (data or {}).get("use_rag", True)

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    def generate():
        try:
            for token in stream_chat(query, model=model, use_rag=use_rag):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Upload and ingest a document file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Use PDF, TXT, or MD"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        chunks = ingest_file(filepath)
        return jsonify({
            "message": f"✅ '{filename}' ingested successfully",
            "chunks": chunks,
            "total_docs": get_document_count(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents", methods=["GET"])
def api_documents():
    """List uploaded documents and chunk count."""
    data_dir = app.config["UPLOAD_FOLDER"]
    files = []
    for f in os.listdir(data_dir):
        if Path(f).suffix.lower() in {".pdf", ".txt", ".md"}:
            filepath = os.path.join(data_dir, f)
            files.append({
                "name": f,
                "size": os.path.getsize(filepath),
                "type": Path(f).suffix.upper().lstrip("."),
            })
    return jsonify({
        "files": files,
        "total_chunks": get_document_count(),
    })


@app.route("/api/documents/clear", methods=["POST"])
def api_clear():
    """Clear all indexed documents from vector store."""
    try:
        clear_collection()
        return jsonify({"message": "✅ Vector store cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models", methods=["GET"])
def api_models():
    """List available Ollama models."""
    return jsonify({"models": list_models()})


@app.route("/api/status", methods=["GET"])
def api_status():
    """Health check and status endpoint."""
    return jsonify({
        "status": "running",
        "indexed_chunks": get_document_count(),
        "models": list_models(),
    })


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)

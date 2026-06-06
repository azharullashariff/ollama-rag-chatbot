# 🤖 Ollama RAG Chatbot

A **private AI chatbot** powered by [Ollama](https://ollama.com) (local LLM) and **Retrieval-Augmented Generation (RAG)** using your own documents. Everything runs locally — no API keys, no data leaving your server.

---

## ✨ Features

- 🧠 **Local LLM** via Ollama (Llama3, Mistral, Phi3, Gemma, etc.)
- 📚 **RAG Pipeline** — answers grounded in your uploaded documents
- 📄 **Document Support** — PDF, TXT, Markdown
- 💬 **Streaming Responses** — real-time token streaming
- 🗂 **Vector Store** — ChromaDB for fast semantic search
- 🎨 **Premium Dark UI** — drag & drop upload, source citations
- 🔒 **100% Private** — runs entirely on your own server

---

## 🏗 Architecture

```
User Question
     │
     ▼
Embedding (sentence-transformers)
     │
     ▼
ChromaDB Vector Search ──► Top-K relevant chunks
     │
     ▼
Prompt = System + Context + Question
     │
     ▼
Ollama LLM (local)
     │
     ▼
Streamed Answer + Source Citations
```

---

## 🚀 Quick Start

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
```

### 2. Clone the Repo

```bash
git clone https://github.com/azharullashariff/ollama-rag-chatbot /opt/app/
cd /opt/app
```

### 3. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 4. Add Your Documents

Drop your PDFs, TXTs, or Markdown files into the `data/` folder.

### 5. Ingest Documents into Vector Store

```bash
python3 ingest.py
```

To reset and re-ingest:
```bash
python3 ingest.py --reset
```

### 6. Run the App

```bash
sudo python3 app.py
```

Open your browser at: `http://<your-server-ip>`

---

## 📁 Project Structure

```
ollama-rag-chatbot/
├── app.py              # Flask web app & REST API
├── chatbot.py          # Ollama LLM integration
├── rag.py              # ChromaDB vector store + retrieval
├── ingest.py           # Document ingestion pipeline
├── data/               # Your documents (not committed)
├── chroma_db/          # Vector store (auto-created, not committed)
├── templates/
│   └── index.html      # Chat UI
├── static/
│   ├── css/style.css   # Premium dark theme
│   └── js/app.js       # Frontend logic
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Configuration

Edit `chatbot.py` to change the default model:
```python
DEFAULT_MODEL = "llama3"   # or: mistral, phi3, gemma2, etc.
```

Edit `rag.py` to tune chunking and retrieval:
```python
CHUNK_SIZE    = 500   # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks
TOP_K         = 5     # chunks retrieved per query
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Chat UI |
| `POST` | `/api/chat` | Non-streaming chat |
| `POST` | `/api/chat/stream` | Streaming chat (SSE) |
| `POST` | `/api/upload` | Upload & ingest a document |
| `GET`  | `/api/documents` | List indexed documents |
| `POST` | `/api/documents/clear` | Clear vector store |
| `GET`  | `/api/models` | List Ollama models |
| `GET`  | `/api/status` | Health check |

---

## 🔧 AWS Setup Notes

Make sure **port 80** is open in your EC2 Security Group:
- Type: HTTP | Port: 80 | Source: 0.0.0.0/0

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Ollama (llama3, mistral, etc.) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | ChromaDB |
| RAG Framework | Custom (no LangChain dependency) |
| Backend | Flask |
| Frontend | Vanilla JS + CSS |

---

## 📄 License

MIT

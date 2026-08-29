# AI Document Intelligence & RAG Platform

> **Production-style learning/portfolio project** — a complete, end-to-end Retrieval-Augmented Generation (RAG) system built to understand modern AI application engineering at a deep level.

---

## What This Is

A web-based AI Document Intelligence platform where you can:

- **Upload** PDF and TXT documents
- **Ask questions** about your documents in natural language
- **Receive grounded answers** with source citations (document name + page number)
- **Inspect** the RAG pipeline internals via a debug mode
- **Evaluate** retrieval and generation quality with a structured test dataset

This is not a ChatGPT wrapper. Every layer — parsing, chunking, embedding, retrieval, prompt construction, generation — is implemented intentionally and explained in detail.

---

## Architecture

```
User
 │
 ▼
React + TypeScript (Vite)
 │  HTTP/JSON
 ▼
FastAPI Backend
 │
 ├─── Document Ingestion ──────────────────────┐
 │     PDF/TXT Parser                          │
 │     Text Cleaning                           │
 │     Chunking                                │
 │     Embedding Generation                   │
 │                                             ▼
 │                                     PostgreSQL + pgvector
 │
 └─── RAG Query Pipeline ─────────────────────┐
       Query Embedding                         │
       Vector Search ──────────────────────────┤
       Keyword Search ─────────────────────────┤
       Hybrid Ranking                          │
       Reranking (optional)                    │
       Context Construction                    │
       LLM Call                                │
       Answer + Citations ◄────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| Data validation | Pydantic v2 |
| ASGI server | Uvicorn |
| Database | PostgreSQL + pgvector |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| PDF parsing | PyMuPDF |
| Frontend | React + TypeScript + Vite |
| Testing | pytest + httpx |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
app/
├── main.py                    # Application factory, CORS, lifespan
├── core/
│   ├── config.py              # Typed configuration (pydantic-settings)
│   ├── logging.py             # Structured logging setup
│   └── exceptions.py         # Custom exception hierarchy + handlers
├── api/
│   ├── router.py              # Central route aggregation
│   └── routes/
│       ├── health.py          # GET /health
│       ├── documents.py       # CRUD /documents
│       ├── search.py          # POST /search
│       └── chat.py            # POST /chat
├── schemas/
│   ├── document.py            # Document request/response models
│   ├── search.py              # Search request/response models
│   └── chat.py                # Chat request/response models (with citations)
└── services/
    └── document_service.py    # Document business logic

tests/
├── conftest.py                # Fixtures, test client, dependency overrides
├── test_health.py
└── test_documents.py

data/documents/                # Place your test documents here (gitignored)
```

---

## Local Setup

### Prerequisites

- Python 3.12+
- pip

### Install

```bash
# Clone the repository
git clone <repository-url>
cd simple-rag

# Create a virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env and fill in your values
```

### Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `AI Document Intelligence` | Application display name |
| `APP_VERSION` | `0.1.0` | Semver version |
| `ENVIRONMENT` | `development` | Runtime environment |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Python log level |
| `API_V1_PREFIX` | `/api/v1` | API route prefix |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | CORS allowed origins |

Phase 2+ variables (add when needed):

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key (never commit!) |
| `OPENAI_EMBEDDING_MODEL` | Embedding model name |
| `OPENAI_CHAT_MODEL` | Chat completion model name |

---

## API Reference

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |

### Documents

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/documents` | Register a document |
| GET | `/api/v1/documents` | List all documents |
| GET | `/api/v1/documents/{id}` | Get document by ID |
| DELETE | `/api/v1/documents/{id}` | Delete a document |

### Search (Phase 5+)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/search` | Semantic/keyword/hybrid search |

### Chat (Phase 10+)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/chat` | RAG-powered Q&A |

---

## Running Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run a specific test file
pytest tests/test_documents.py -v

# Run a specific test
pytest tests/test_documents.py::TestCreateDocument::test_create_document_returns_201 -v

# Run with coverage (install pytest-cov first)
pytest tests/ --cov=app --cov-report=term-missing
```

### Expected Output (Phase 1)

```
tests/test_health.py::test_health_returns_200                           PASSED
tests/test_health.py::test_health_response_has_required_fields          PASSED
tests/test_health.py::test_health_status_is_ok                          PASSED
tests/test_health.py::test_health_timestamp_is_iso8601                  PASSED
tests/test_health.py::test_health_content_type_is_json                  PASSED
tests/test_documents.py::TestCreateDocument::test_create_document_returns_201          PASSED
... (27 total tests)
```

---

## Build Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Complete | FastAPI foundation, CRUD stubs, tests |
| 2 | 🔜 Next | Document upload, PDF/TXT parsing |
| 3 | 📋 Planned | Chunking (size, overlap, strategies) |
| 4 | 📋 Planned | Embeddings + pgvector storage |
| 5 | 📋 Planned | Vector search |
| 6 | 📋 Planned | Metadata filtering |
| 7 | 📋 Planned | Keyword search |
| 8 | 📋 Planned | Hybrid search (RRF) |
| 9 | 📋 Planned | Reranking |
| 10 | 📋 Planned | Full RAG pipeline |
| 11 | 📋 Planned | Source citations |
| 12 | 📋 Planned | Structured output |
| 13 | 📋 Planned | Conversational RAG |
| 14 | 📋 Planned | RAG evaluation |
| 15–20 | 📋 Planned | Prompt testing, security, observability, Docker, frontend |

---

## Security Notes

- API keys are **never** committed to version control
- Use `.env` for local secrets; `.env.example` contains only placeholders
- Document contents are not logged
- CORS is configured for specific origins, not `*`

---

## Known Limitations (Phase 1)

- Storage is **in-memory** — data resets on every server restart
- No file upload yet — documents are registered via JSON metadata only
- Search and chat are **stub endpoints** — they return empty/placeholder responses
- No authentication or authorisation

These are all intentional — this is a learning project built phase by phase.

---

## License

MIT — see LICENSE file.

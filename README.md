# DocuMind AI — RAG Document Intelligence Platform

DocuMind AI is an end-to-end Retrieval-Augmented Generation (RAG) system built with FastAPI, PostgreSQL (`pgvector`), Google Gemini, and React. 

Upload your PDF or TXT documents (resumes, policies, reports), ask questions in natural language, and get grounded answers with source citations (file name + page numbers).

---

## Key Features

- **Document Ingestion & Parsing:** Upload PDF and TXT documents. Files are validated, deduplicated using SHA-256 content hashing, and parsed page-by-page using PyMuPDF.
- **Recursive Text Chunking:** Splits document text into overlapping chunks (~1000 characters, 200-character overlap) prioritizing paragraph and sentence boundaries.
- **Vector Search (`pgvector`):** Generates 768-dimensional embeddings via Google Gemini (`text-embedding-004`) and performs cosine similarity search directly inside PostgreSQL.
- **Grounded Q&A (Zero Hallucination):** Answers user prompts using Google Gemini 2.0 Flash (`gemini-2.0-flash`). Enforces strict system prompts and temperature `0.0` so the AI refuses to answer if information is not present in the uploaded context.
- **Automated Evaluation Harness:** Includes an "LLM-as-a-Judge" evaluation script (`scripts/evaluate.py`) to programmatically score RAG accuracy.
- **Modern Light Theme UI:** Clean, responsive single-page application built with React and Vite.

---

## Architecture

```
User (Browser)
    │
    ▼
React + Vite Frontend (Vercel)
    │  HTTP / REST API
    ▼
FastAPI Backend (Render)
    │
    ├─── Ingestion Pipeline ──────────────────────┐
    │     PyMuPDF Text Parser                      │
    │     Recursive Chunking                       │
    │     Gemini Embedding Service                 │
    │                                              ▼
    │                                     PostgreSQL + pgvector (Neon)
    │                                              ▲
    └─── RAG Search & Chat Pipeline ───────────────┤
          Question Vectorization ──────────────────┘
          Cosine Distance Search (<=>)
          Prompt Construction (Context + Question)
          Gemini 2.0 Flash Generation
          Grounded Answer + Page Citations ───────► User
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React, Vite, Custom CSS Design System |
| **Backend Framework** | FastAPI (Python 3.12+), Uvicorn (ASGI) |
| **Data Validation & Config** | Pydantic v2, `pydantic-settings` |
| **Database & Vectors** | PostgreSQL + `pgvector` (AsyncSQLAlchemy, `asyncpg`) |
| **AI / LLM Integration** | Google Gemini (`gemini-2.0-flash`, `text-embedding-004`) |
| **PDF Parsing** | PyMuPDF |
| **Deployment** | Vercel (Frontend), Render (Backend), Neon (Database) |

---

## Project Structure

```
.
├── app/                          # FastAPI Backend Application
│   ├── main.py                   # App factory, CORS, lifespan
│   ├── api/                      # REST API Routes
│   │   ├── router.py             # Route aggregator
│   │   └── routes/               # Health, Documents, Search, Chat
│   ├── core/                     # Config, Logging, Exception Handlers
│   ├── db/                       # Async Engine, ORM Models (Document & Chunk)
│   ├── repositories/             # Database Access Layer (pgvector queries)
│   ├── schemas/                  # Pydantic Request/Response contracts
│   └── services/                 # Business logic (Ingestion, Parser, Chunking, Embedding, RAG)
├── data/                         # Evaluation datasets & test files
├── docs/                         # Architecture & Deployment Documentation
├── frontend/                     # React + Vite Frontend Application
│   ├── src/                      # App layout, Components, API services, Styles
│   ├── index.html
│   └── vite.config.js
├── scripts/                      # Evaluation harness & database helpers
│   └── evaluate.py
├── pyproject.toml                # Backend dependencies
└── requirements.txt              # Render build requirements
```

---

## API Endpoints

### Health Check
- `GET /health` — Verifies backend status and database connectivity.

### Document Management
- `POST /api/v1/documents` — Upload a PDF or TXT file (multipart/form-data).
- `GET /api/v1/documents` — List all uploaded documents, newest first.
- `GET /api/v1/documents/{document_id}` — Get document metadata and status.
- `DELETE /api/v1/documents/{document_id}` — Delete a document and its chunks.

### RAG Search & Chat
- `POST /api/v1/search` — Perform vector similarity search across all document chunks.
- `POST /api/v1/chat` — Ask a question; returns a grounded answer with page citations.

---

## Quickstart Guide

### 1. Clone & Setup Backend

```bash
# Clone repository
git clone https://github.com/BarotMeet05/simple-rag-fastapi.git
cd simple-rag-fastapi

# Create & activate virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
APP_NAME="DocuMind AI"
ENVIRONMENT="development"
DEBUG=true

# Database URL (Local PostgreSQL or Neon Cloud)
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/ragdb"

# Google Gemini API Key
GEMINI_API_KEY="your-gemini-api-key"
```

### 3. Run Backend & Frontend

**Terminal 1 (Backend):**
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API Docs: http://localhost:8000/docs

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
npm run dev
```
- Frontend UI: http://localhost:5173

---

## RAG Evaluation Harness

To run automated accuracy testing against a sample test document using LLM-as-a-Judge:

```bash
python scripts/evaluate.py
```

---

## Deployment

Detailed deployment instructions for free hosting:
- **Frontend:** Vercel
- **Backend:** Render
- **Database:** Neon PostgreSQL

See [docs/PHASE_7_README.md](docs/PHASE_7_README.md) for step-by-step instructions.

---

## License

MIT License — see `LICENSE` for details.

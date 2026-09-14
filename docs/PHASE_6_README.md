# Phase 6: Frontend (React + Vite)

## What was built in this phase?

We created a premium, dark-themed Single Page Application (SPA) using React and Vite. The frontend provides two core features:

1. **Document Upload** — A drag-and-drop sidebar to upload PDFs and TXT files, with a live document list showing status and chunk counts.
2. **AI Chat Interface** — A ChatGPT-style conversation window where users can ask questions about their documents and receive grounded answers with citation chips.

### Design Highlights
- **Dark theme** with deep navy background and violet accent gradient
- **Glassmorphism** effects on message bubbles (frosted glass)
- **Micro-animations** — messages fade in, loading dots bounce, processing status pulses
- **Inter font** from Google Fonts for clean, modern typography
- Only **7 source files** — intentionally minimal and easy to understand

### Architecture
The frontend follows a simple 3-layer pattern:
- `App.jsx` → Layout (sidebar + chat)
- `components/` → UI building blocks (DocumentUploader, ChatInterface)
- `services/api.js` → All `fetch()` calls to the FastAPI backend

### How it connects to the backend
- **During local development:** Vite's proxy in `vite.config.js` forwards `/api/*` requests from port 5173 to port 8000, avoiding all CORS issues.
- **In production (Vercel):** The `VITE_API_URL` environment variable points to your Render backend URL.

## How to run locally

1. Open a terminal and start the **backend**:
   ```bash
   cd Simple_RAG
   .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
   ```

2. Open a **second terminal** and start the **frontend**:
   ```bash
   cd Simple_RAG/frontend
   npm run dev
   ```

3. Open your browser to **http://localhost:5173**

## Documentation
- [Backend Architecture Walkthrough](./BACKEND_ARCHITECTURE.md) — Every file and layer in the FastAPI backend explained
- [Frontend Architecture Walkthrough](./FRONTEND_ARCHITECTURE.md) — Every file, React concept, and design decision in the frontend explained

## Next Steps (Phase 7)
Deploy the full stack: frontend to Vercel, backend to Render, database on Neon — all on free tiers!

# Phase 3: Chunking & Embeddings

## What was built in this phase?

In Phase 3, we extended our document ingestion pipeline. In Phase 2, we successfully extracted text from PDFs and TXT files. But you can't just pass 100 pages of text into an LLM all at once—it exceeds the context window, gets slow, and causes "lost in the middle" phenomena (where the LLM ignores stuff in the middle of a huge prompt).

To fix this, we implemented **Chunking** and **Embeddings**.

### 1. Chunking (`chunking_service.py`)
We built a text splitter that takes extracted text and breaks it into overlapping blocks (chunks) of around 1,000 characters. 
- **Why overlap?** If a sentence spans the 1,000-character mark, splitting exactly at 1,000 would chop a sentence in half, destroying its meaning. A 200-character overlap ensures that context isn't lost across chunk boundaries.
- Our custom chunker attempts to split on natural boundaries (like double newlines) first.

### 2. Embeddings (`embedding_service.py`)
Once we have chunks, we need a way to mathematically compare their meaning to a user's question later.
- We integrate the **Google GenAI SDK** (`google-genai`).
- We use the `text-embedding-004` model.
- An embedding is a vector (a list of floating-point numbers). This model returns 768 numbers per chunk. These numbers represent the semantic "meaning" of the text.

### 3. Database Storage (`pgvector`)
We can't just store vectors as plain strings; we need to perform lightning-fast math (cosine similarity) on them in the next phase.
- We added `pgvector` to our PostgreSQL database setup.
- We created a new SQLAlchemy model: `DocumentChunkModel`.
- We added a column of type `Vector(768)` to store the Gemini embeddings natively in the database.

### 4. Pipeline Integration (`ingestion_service.py`)
We updated the ingestion orchestrator. The flow is now:
`Upload -> Validate -> Hash -> Save to DB -> Parse Text -> CHUNK TEXT -> EMBED CHUNKS -> Save Chunks to DB -> Mark READY`.

## Running it locally

1. **API Key**: You need a free Google Gemini API key. Get one from [Google AI Studio](https://aistudio.google.com/).
2. Add it to your `.env` file:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```
3. The next time you upload a document, it will be chunked, embedded, and stored in the database automatically.

## Next Steps (Phase 4)
Now that our documents are chopped up and translated into math, Phase 4 will introduce **Vector Search**. When a user asks a question, we will embed their question into a vector, ask PostgreSQL to find the most mathematically similar document chunks, and pass those chunks to Gemini to answer the question!

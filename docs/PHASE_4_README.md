# Phase 4: Vector Search & RAG Chat

## What was built in this phase?

In Phase 4, we completed the core AI capability of this project: the **Retrieval-Augmented Generation (RAG)** pipeline.

Now, instead of just storing documents, the application can actually answer questions about them.

### 1. Vector Search (`document_repository.py`)
We added the `search_similar_chunks` method. This uses `pgvector`'s cosine distance operator (`<=>`). 
When a user asks a question, we turn that question into a vector (a 768-dimension coordinate). PostgreSQL then instantly finds the chunks of text whose coordinates are mathematically closest to the question's coordinates.

### 2. LLM Generation (`llm_service.py`)
We created a dedicated service for the Gemini LLM (`gemini-2.0-flash`). 
- **Strict Prompting:** We added a strong `RAG_SYSTEM_PROMPT` instructing the model to *only* answer using the provided context and to refuse if the answer isn't there.
- **Zero Temperature:** We set `temperature=0.0` to make the model deterministic and factual, preventing "hallucinations" (making things up).

### 3. RAG Orchestration (`rag_service.py`)
This service acts as the conductor. When you ask a question:
1. It calls the `EmbeddingService` to vectorize your question.
2. It asks the `DocumentRepository` for the top 5 closest chunks.
3. It packages those 5 chunks into a string of "Context".
4. It sends the Context + Question to the `LLMService`.
5. It returns the final answer, plus the exact sources (filenames and page numbers) it used.

### 4. API Endpoints (`search.py` & `chat.py`)
We replaced the Phase 1 "stubs" with the real implementation. 
- `POST /api/v1/search`: Returns raw chunks based on a query (great for debugging).
- `POST /api/v1/chat`: Returns the fully generated answer and citations.

## How to test this locally

Make sure your local API is running (`uvicorn app.main:app --reload`).

1. Open your browser to `http://localhost:8000/docs`.
2. Ensure you have uploaded at least one document (e.g., a company policy).
3. Open the **`POST /api/v1/chat`** endpoint.
4. Click **Try it out** and enter a question like:
   ```json
   {
     "question": "What is the policy on deploying code on Fridays?",
     "top_k": 5
   }
   ```
5. Execute! You should get back a beautiful answer grounded perfectly in your document, complete with a list of the exact chunks the LLM read to find the answer.

## Next Steps (Phase 5)
Phase 5 will focus on **Evaluation**. How do we know if our RAG system is actually good? We will build a simple evaluation script that tests our retrieval accuracy and generation quality!

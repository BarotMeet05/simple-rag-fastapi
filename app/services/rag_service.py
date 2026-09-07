# app/services/rag_service.py
"""
RAG Service — Retrieval-Augmented Generation Orchestrator
==========================================================
This service owns the end-to-end RAG pipeline for answering user questions.

Flow for semantic search:
1. Embed the user query
2. Search DB for nearest chunks
3. Return chunks

Flow for RAG chat:
1. Embed the user query
2. Search DB for nearest chunks
3. Construct context
4. Generate answer via LLMService
5. Return answer + sources
"""

from pydantic import BaseModel
from typing import List

from app.core.logging import get_logger
from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

logger = get_logger(__name__)

# Output models
class ChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    text: str

class RAGResponse(BaseModel):
    answer: str
    sources: List[ChunkResponse]

class RAGService:
    def __init__(self, repository: DocumentRepository):
        self.repository = repository
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        
    async def search(self, query: str, limit: int = 5) -> List[ChunkResponse]:
        """
        Perform a semantic search for the most relevant document chunks.
        """
        logger.info(f"Performing semantic search for: '{query}'")
        
        # 1. Embed the query
        query_embeddings = await self.embedding_service.get_embeddings([query])
        if not query_embeddings:
            logger.warning("Could not generate embedding for query.")
            return []
            
        query_vector = query_embeddings[0]
        
        # 2. Search the database
        results = await self.repository.search_similar_chunks(query_vector, limit=limit)
        
        # 3. Format the results
        formatted_results = []
        for chunk, doc in results:
            formatted_results.append(
                ChunkResponse(
                    chunk_id=str(chunk.chunk_id),
                    document_id=str(doc.document_id),
                    filename=doc.filename,
                    page_number=chunk.page_number,
                    text=chunk.text_content,
                )
            )
            
        return formatted_results
        
    async def chat(self, question: str, limit: int = 5) -> RAGResponse:
        """
        Answer a question using RAG (search + generate).
        """
        logger.info(f"Answering RAG question: '{question}'")
        
        # 1. Search for relevant context
        sources = await self.search(question, limit=limit)
        
        if not sources:
            return RAGResponse(
                answer="I couldn't find any relevant documents to answer your question. Please ensure documents are uploaded and processed.",
                sources=[]
            )
            
        # 2. Prepare context for the LLM
        context_chunks = [
            {
                "filename": source.filename,
                "page_number": source.page_number,
                "text": source.text
            }
            for source in sources
        ]
        
        # 3. Generate the answer
        answer = await self.llm_service.generate_answer(question, context_chunks)
        
        # 4. Return both the answer and the exact sources used
        return RAGResponse(
            answer=answer,
            sources=sources
        )

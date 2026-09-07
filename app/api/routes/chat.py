# app/api/routes/chat.py
"""
Chat Route — Phase 4
====================
This route integrates the complete RAG pipeline:
Embedding the question -> Searching for context -> Generating the answer.
"""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.rag_service import RAGService

router = APIRouter()

def get_rag_service(db: AsyncSession = Depends(get_db)) -> RAGService:
    repository = DocumentRepository(db)
    return RAGService(repository)

@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Chat"],
    summary="Ask a question about your documents",
    description="Generates an answer to your question based on the indexed document chunks.",
)
async def chat(
    request: ChatRequest,
    service: RAGService = Depends(get_rag_service),
) -> ChatResponse:
    """
    POST /chat
    """
    conversation_id = request.conversation_id or uuid.uuid4()
    
    rag_response = await service.chat(question=request.question, limit=request.top_k)
    
    sources = []
    for source in rag_response.sources:
        sources.append(
            Source(
                chunk_id=source.chunk_id,
                document_id=uuid.UUID(source.document_id),
                document_name=source.filename,
                page_number=source.page_number,
                relevance_score=1.0, # Dummy for now
                text_preview=source.text[:200] if request.debug else None
            )
        )

    return ChatResponse(
        answer=rag_response.answer,
        conversation_id=conversation_id,
        sources=sources,
        is_grounded=len(sources) > 0,
        debug=None,
    )

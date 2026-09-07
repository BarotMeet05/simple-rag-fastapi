# app/api/routes/search.py
"""
Search Route — Phase 4
======================
This route uses the RAGService to perform semantic vector search
over the document chunks.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.search import SearchRequest, SearchResponse, ChunkResult
from app.services.rag_service import RAGService

router = APIRouter()

def get_rag_service(db: AsyncSession = Depends(get_db)) -> RAGService:
    repository = DocumentRepository(db)
    return RAGService(repository)

@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Search"],
    summary="Semantic document search",
    description="Search across all indexed document chunks using vector semantic search.",
)
async def search_documents(
    request: SearchRequest,
    service: RAGService = Depends(get_rag_service),
) -> SearchResponse:
    """
    POST /search
    """
    results = await service.search(query=request.query, limit=request.top_k)
    
    chunk_results = []
    for i, res in enumerate(results):
        chunk_results.append(
            ChunkResult(
                chunk_id=res.chunk_id,
                document_id=res.document_id,
                document_name=res.filename,
                page_number=res.page_number,
                text=res.text,
                similarity_score=1.0, # Dummy score for now, pgvector distance could be mapped here
                chunk_index=i,
            )
        )
        
    return SearchResponse(
        query=request.query,
        results=chunk_results,
        total_results=len(chunk_results),
        search_type_used="vector",
        embedding_latency_ms=None,
        retrieval_latency_ms=None,
    )

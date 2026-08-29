# app/api/routes/search.py
"""
Search Route — Phase 1 Stub
============================
This endpoint is intentionally not implemented yet.

WHY stub it out now?
---------------------
1. The API contract is defined early — tests can be written against the interface
2. The frontend can start being built against a real endpoint (it returns real JSON)
3. It documents what the system WILL do, which helps architecture discussions
4. You can run the server and see the endpoint in Swagger UI immediately

The stub returns a structured "not yet implemented" response rather than a
500 error, so callers know the endpoint exists but the feature is pending.
"""

from fastapi import APIRouter, status

from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Search"],
    summary="Semantic / keyword / hybrid document search",
    description=(
        "Search across all indexed document chunks. "
        "Supports vector (semantic), keyword, and hybrid search strategies. "
        "**Phase 5+ implementation.**"
    ),
)
async def search_documents(request: SearchRequest) -> SearchResponse:
    """
    POST /search — Phase 1 stub.

    Returns an empty result set with a note that this feature is coming soon.
    """
    return SearchResponse(
        query=request.query,
        results=[],
        total_results=0,
        search_type_used=request.search_type,
        embedding_latency_ms=None,
        retrieval_latency_ms=None,
    )

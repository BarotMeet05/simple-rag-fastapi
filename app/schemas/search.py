# app/schemas/search.py
"""
Search Schemas
==============
Even though search is a stub in Phase 1, defining the schemas now has value:
- Forces us to think about the search API contract upfront
- The frontend and tests can be written against a stable interface
- We'll fill in the implementation in Phases 5–8

Search result anatomy (for context):
--------------------------------------
A search result in a RAG system is not just "a document" — it's a CHUNK
of a document, with metadata that lets us:
1. Show the user WHERE the answer came from (document name + page)
2. Rank results by relevance (similarity score)
3. Construct context for the LLM (chunk text)

This will make much more sense when we build the chunking phase.
"""

from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Request
# =============================================================================


class SearchFilters(BaseModel):
    """
    Optional filters to narrow the search scope.

    Example: A user might say "search only in policy.pdf" — this translates
    to document_id filter before vector similarity is computed.
    (Phase 6 implements this properly.)
    """

    document_id: UUID | None = Field(default=None, description="Restrict search to a specific document")
    file_type: str | None = Field(default=None, description="Restrict search to a specific file type")


class SearchRequest(BaseModel):
    """Body for POST /search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language search query",
        examples=["What is the property coverage limit?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return. Higher values increase recall but add LLM context.",
    )
    filters: SearchFilters | None = Field(default=None, description="Optional metadata filters")
    search_type: str = Field(
        default="hybrid",
        description="Search strategy: 'vector', 'keyword', or 'hybrid'",
        examples=["hybrid"],
    )


# =============================================================================
# Response
# =============================================================================


class ChunkResult(BaseModel):
    """A single retrieved chunk with its metadata."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: UUID = Field(..., description="Parent document")
    document_name: str = Field(..., description="Original filename")
    page_number: int | None = Field(default=None, description="Page number (PDF only)", ge=1)
    text: str = Field(..., description="The chunk text content")
    similarity_score: float = Field(..., description="Relevance score (0–1, higher is better)", ge=0.0, le=1.0)
    chunk_index: int = Field(..., description="Position of this chunk within the document", ge=0)


class SearchResponse(BaseModel):
    """Response from POST /search."""

    query: str = Field(..., description="Echo of the search query")
    results: list[ChunkResult] = Field(..., description="Ranked search results")
    total_results: int = Field(..., description="Number of results returned", ge=0)
    search_type_used: str = Field(..., description="Which search strategy was executed")
    # Latency fields — filled in from Phase 5 onwards
    embedding_latency_ms: float | None = Field(default=None, description="Time to embed the query")
    retrieval_latency_ms: float | None = Field(default=None, description="Time to retrieve from DB")

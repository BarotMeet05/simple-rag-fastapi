# app/schemas/chat.py
"""
Chat Schemas
============
The RAG pipeline's final output: a grounded answer with citations.

Key design decision — citations are not optional:
-------------------------------------------------
Every ChatResponse MUST include a sources list (even if empty).
This forces the downstream code to always think about attribution.
It also means the frontend always has a consistent shape to render.

Conversation ID:
---------------
A UUID passed back and forth between client and server to maintain
conversation context. The client:
1. Sends no conversation_id on the first message
2. Receives a conversation_id in the response
3. Sends that conversation_id on every subsequent message

This stateless design (server doesn't push IDs to clients; clients echo them
back) is a standard REST pattern you'll recognise from Go services.
"""

from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Request
# =============================================================================


class ChatRequest(BaseModel):
    """Body for POST /chat."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question about their documents",
        examples=["What is the property coverage limit?"],
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Pass to continue an existing conversation. Omit for a new conversation.",
    )
    # Optional search configuration — lets the client tune retrieval per-request
    top_k: int = Field(default=5, ge=1, le=20, description="Chunks to retrieve for context")
    search_type: str = Field(default="hybrid", description="Retrieval strategy")
    # Restrict RAG to specific documents
    document_ids: list[UUID] | None = Field(
        default=None,
        description="Limit retrieval to these documents. Null means search all documents.",
    )
    debug: bool = Field(
        default=False,
        description="Include debug information (retrieved chunks, latencies) in the response",
    )


# =============================================================================
# Response
# =============================================================================


class Source(BaseModel):
    """
    A citation pointing to a specific chunk in a specific document.

    This is the traceability chain:
        LLM answer → retrieved chunk → document → page

    Without this, you can't answer: "Where did the AI get that from?"
    That's unacceptable in any enterprise RAG system.
    """

    chunk_id: str = Field(..., description="Identifier of the retrieved chunk")
    document_id: UUID = Field(..., description="Parent document UUID")
    document_name: str = Field(..., description="Human-readable filename")
    page_number: int | None = Field(default=None, description="Page number within the document")
    relevance_score: float = Field(..., description="How relevant this chunk was to the query", ge=0.0, le=1.0)
    # Included in debug mode only
    text_preview: str | None = Field(default=None, description="First 200 chars of the chunk text (debug mode)")


class DebugInfo(BaseModel):
    """
    Internal pipeline information — only included when debug=True.

    This is the 'glass box' that helps you understand:
    - Which chunks were retrieved (and whether the right ones were)
    - How long each stage took
    - Whether a retrieval failure or a generation failure caused a bad answer
    """

    retrieved_chunks: list[dict] = Field(default_factory=list)
    query_embedding_latency_ms: float | None = None
    retrieval_latency_ms: float | None = None
    reranking_latency_ms: float | None = None
    llm_latency_ms: float | None = None
    total_latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    search_type_used: str | None = None
    top_k_used: int | None = None


class ChatResponse(BaseModel):
    """Response from POST /chat."""

    answer: str = Field(..., description="The LLM-generated answer")
    conversation_id: UUID = Field(..., description="Use this in subsequent requests to continue the conversation")
    sources: list[Source] = Field(
        default_factory=list,
        description="Citations supporting the answer. Empty if answer couldn't be grounded.",
    )
    # Set to True when the model couldn't find supporting evidence
    is_grounded: bool = Field(
        default=True,
        description="False when the answer is 'I could not find sufficient information'",
    )
    debug: DebugInfo | None = Field(
        default=None,
        description="Populated only when the request included debug=true",
    )

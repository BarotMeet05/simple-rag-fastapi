# app/api/routes/chat.py
"""
Chat Route — Phase 1 Stub
==========================
Same philosophy as search.py — stub the endpoint early so the API contract
is defined and the system is testable end-to-end structurally.

The real RAG pipeline (Phases 10–13) will replace this stub body entirely.
"""

import uuid

from fastapi import APIRouter, status

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Chat"],
    summary="Ask a question about your documents",
    description=(
        "Submit a natural language question. The system retrieves relevant document "
        "chunks and generates a grounded answer with citations. "
        "**Phase 10+ implementation.**"
    ),
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    POST /chat — Phase 1 stub.

    Returns a placeholder answer indicating the feature is not yet implemented.
    The response shape is correct — the frontend can be built against it.
    """
    conversation_id = request.conversation_id or uuid.uuid4()

    return ChatResponse(
        answer=(
            "The RAG pipeline is not yet implemented. "
            "This stub confirms the API endpoint is reachable and the request schema is valid."
        ),
        conversation_id=conversation_id,
        sources=[],
        is_grounded=False,
        debug=None,
    )

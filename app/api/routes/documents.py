# app/api/routes/documents.py
"""
Document API Routes (Phase 2 — Real File Upload)
=================================================
Changes from Phase 1:
- POST /documents now accepts multipart/form-data (file upload)
- DocumentService now depends on AsyncSession (PostgreSQL)
- The service interface is otherwise unchanged

multipart/form-data explained:
-------------------------------
When a browser or API client uploads a file, it uses multipart/form-data
encoding. The HTTP request body is split into multiple "parts" separated by
a boundary string. Each part has its own headers (Content-Disposition, Content-Type)
followed by the part's content.

Example multipart body (simplified):
    --boundary
    Content-Disposition: form-data; name="file"; filename="policy.pdf"
    Content-Type: application/pdf

    <binary PDF bytes>
    --boundary--

FastAPI's UploadFile:
---------------------
FastAPI wraps the multipart part in an UploadFile object:
    file.filename     → "policy.pdf"
    file.content_type → "application/pdf"
    await file.read() → bytes (the actual file content)

WHY await file.read()?
Reading the file content is an I/O operation (reading from the request stream).
await lets the event loop do other work while waiting for the data.

Form() vs Body():
-----------------
In Phase 1, POST /documents used Body() (JSON body).
In Phase 2, it uses File() + Form() (multipart).
You cannot mix JSON body and File() in the same request — multipart and JSON
are different encoding formats. This is why description becomes a Form field.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.document_service import DocumentService

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Dependency provider
# =============================================================================
# Phase 2: DocumentService now needs a DB session.
# get_db() is a generator that yields an AsyncSession for the request duration.
# Closing/committing is handled automatically by get_db().
# =============================================================================


def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    """Dependency provider: create DocumentService with the request's DB session."""
    return DocumentService(db)


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
    summary="Upload a document",
    description=(
        "Upload a PDF or TXT document. The file is validated, parsed, "
        "and stored. Processing happens synchronously — the response is "
        "returned only after parsing is complete."
    ),
    responses={
        409: {"description": "Duplicate document (same file content already uploaded)"},
        413: {"description": "File too large"},
        422: {"description": "Unsupported file type or validation failure"},
    },
)
async def upload_document(
    # File() tells FastAPI to read this field from the multipart body as a file
    file: UploadFile = File(..., description="PDF or TXT file to upload"),
    # Form() tells FastAPI this is a regular form field (not a file)
    description: str | None = Form(default=None, description="Optional document description"),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """
    POST /documents — accepts multipart/form-data

    Flow:
    1. FastAPI parses the multipart body, gives us an UploadFile
    2. We read the bytes from the upload stream
    3. We pass bytes + metadata to the service
    4. Service validates, deduplicates, saves, parses
    5. We return the DocumentResponse
    """
    # Read all bytes from the upload stream
    # For large files in production, you'd stream to disk instead of reading all at once
    # (Phase 18 performance optimisation)
    file_bytes = await file.read()

    return await service.ingest_document(
        file_bytes=file_bytes,
        filename=file.filename or "unknown",
        content_type=file.content_type,
        description=description,
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Documents"],
    summary="List all documents",
    description="Returns all uploaded documents, sorted newest first.",
)
async def list_documents(
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """GET /documents"""
    return await service.list_documents()


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Documents"],
    summary="Get a specific document",
    responses={404: {"description": "Document not found"}},
)
async def get_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """GET /documents/{document_id}"""
    return await service.get_document(document_id)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Documents"],
    summary="Delete a document",
    responses={404: {"description": "Document not found"}},
)
async def delete_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> None:
    """DELETE /documents/{document_id}"""
    await service.delete_document(document_id)

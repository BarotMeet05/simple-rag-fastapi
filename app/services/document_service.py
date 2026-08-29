# app/services/document_service.py
"""
Document Service — Business Logic Layer (Phase 2 update)
=========================================================
Phase 1: In-memory dict storage (educational stub)
Phase 2: PostgreSQL via DocumentRepository + real file ingestion

What changed from Phase 1?
---------------------------
- Storage backend: dict → PostgreSQL
- Create: JSON metadata → real file upload + ingestion pipeline
- All queries delegate to DocumentRepository (no SQL here)
- DocumentModel → DocumentResponse conversion (ORM model → Pydantic schema)

What stayed the same?
---------------------
- Route handlers still call the service layer (no direct DB access in routes)
- The service interface (method signatures) is largely unchanged
- Exception types (NotFoundError, ConflictError) are unchanged

This is the value of the layered architecture: we swapped the ENTIRE storage
backend without touching a single route handler.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models import DocumentModel
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentListResponse, DocumentResponse, FileType, ProcessingStatus
from app.services.ingestion_service import IngestionService

logger = get_logger(__name__)


def _model_to_response(doc: DocumentModel) -> DocumentResponse:
    """
    Convert a SQLAlchemy ORM model to a Pydantic response schema.

    WHY this conversion?
    The ORM model (DocumentModel) is a SQLAlchemy object tied to a DB session.
    We cannot return it directly from a FastAPI route — FastAPI needs a Pydantic
    model to serialize to JSON.

    This mapper function isolates the conversion logic. If the API schema
    diverges from the DB schema (e.g., we rename a column), only this function
    needs updating.
    """
    return DocumentResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        file_type=FileType(doc.file_type),
        file_size_bytes=doc.file_size_bytes,
        processing_status=ProcessingStatus(doc.processing_status),
        description=doc.description,
        uploaded_at=doc.uploaded_at,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


class DocumentService:
    """
    Manages document lifecycle: ingest, read, delete.

    Phase 2: delegates storage to DocumentRepository (PostgreSQL).
             delegates file processing to IngestionService.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = DocumentRepository(db)
        self.ingestion = IngestionService(self.repository)

    # =========================================================================
    # Create (ingest)
    # =========================================================================

    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
        description: str | None = None,
    ) -> DocumentResponse:
        """
        Run the full ingestion pipeline and return the resulting document.

        Delegates to IngestionService which handles:
        - validation
        - duplicate detection
        - file storage
        - parsing
        - status updates
        """
        doc = await self.ingestion.ingest(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            description=description,
        )
        return _model_to_response(doc)

    # =========================================================================
    # Read
    # =========================================================================

    async def list_documents(self) -> DocumentListResponse:
        """Return all documents sorted newest-first."""
        docs = await self.repository.list_all()
        responses = [_model_to_response(d) for d in docs]
        return DocumentListResponse(
            documents=responses,
            total=len(responses),
        )

    async def get_document(self, document_id: uuid.UUID) -> DocumentResponse:
        """
        Return a single document by ID.

        Raises:
            NotFoundError: if the document does not exist.
        """
        doc = await self.repository.get_by_id(document_id)
        if doc is None:
            raise NotFoundError(f"Document '{document_id}' not found.")
        return _model_to_response(doc)

    # =========================================================================
    # Delete
    # =========================================================================

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """
        Delete a document record.

        Note: This does NOT delete the file from disk (Phase 2 limitation).
        Phase 16 (security) will add file cleanup on delete.

        Raises:
            NotFoundError: if the document does not exist.
        """
        deleted = await self.repository.delete(document_id)
        if not deleted:
            raise NotFoundError(f"Document '{document_id}' not found.")
        logger.info("Document deleted: id=%s", document_id)

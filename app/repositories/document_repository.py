# app/repositories/document_repository.py
"""
Document Repository — Database Access Layer
============================================
This module is the ONLY place that contains SQL/ORM queries for documents.

Repository Pattern:
-------------------
            Route Handler
                 │
            DocumentService   ← business logic, no SQL
                 │
         DocumentRepository   ← ALL SQL queries live here
                 │
            PostgreSQL

Benefits:
1. Unit test the service with a mock repository (no real DB)
2. Swap the DB backend without touching service logic
3. All queries in one file — easy to review, optimise, add indexes

SQLAlchemy async query style:
------------------------------
Traditional (sync):   db.query(DocumentModel).filter(...)
Modern (async v2):    await db.execute(select(DocumentModel).where(...))

We always use the modern style (select() function), which works with both
sync and async SQLAlchemy and is more explicit.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import DocumentModel, DocumentChunkModel

logger = get_logger(__name__)


class DocumentRepository:
    """
    All database operations for the documents table.

    Instantiated per-request — receives an AsyncSession from the route handler
    via dependency injection.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    # Create
    # =========================================================================

    async def create(self, document: DocumentModel) -> DocumentModel:
        """
        Persist a new document record.

        Note: we add to the session, but do NOT commit here.
        The commit happens in get_db() after the request completes.
        This gives the service layer the ability to do multiple operations
        atomically (all succeed or all roll back together).
        """
        self.db.add(document)
        await self.db.flush()  # flush sends the INSERT without committing
        await self.db.refresh(document)  # reload from DB (gets server-generated defaults)
        logger.debug("Document inserted: id=%s", document.document_id)
        return document

    async def create_chunks(self, chunks: list[DocumentChunkModel]) -> None:
        """
        Batch insert document chunks.
        """
        if not chunks:
            return
            
        self.db.add_all(chunks)
        await self.db.flush()
        logger.debug("Inserted %d chunks", len(chunks))

    # =========================================================================
    # Read
    # =========================================================================

    async def get_by_id(self, document_id: uuid.UUID) -> DocumentModel | None:
        """Return a document by primary key, or None if not found."""
        result = await self.db.execute(
            select(DocumentModel).where(DocumentModel.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, sha256_hash: str) -> DocumentModel | None:
        """
        Return a document by its SHA-256 content hash, or None.

        Used for duplicate detection:
            hash = sha256(file_bytes)
            existing = await repo.get_by_hash(hash)
            if existing:
                raise ConflictError(...)
        """
        result = await self.db.execute(
            select(DocumentModel).where(DocumentModel.sha256_hash == sha256_hash)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[DocumentModel]:
        """Return all documents ordered by upload time (newest first)."""
        result = await self.db.execute(
            select(DocumentModel).order_by(DocumentModel.uploaded_at.desc())
        )
        return list(result.scalars().all())

    # =========================================================================
    # Update
    # =========================================================================

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        *,
        error_message: str | None = None,
        chunk_count: int | None = None,
        page_count: int | None = None,
    ) -> DocumentModel | None:
        """
        Update a document's processing status and related fields.

        The keyword-only arguments (after *) are optional updates.
        Using keyword-only forces callers to be explicit:
            await repo.update_status(id, "ready", chunk_count=42)
        rather than the error-prone positional:
            await repo.update_status(id, "ready", None, 42, None)
        """
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None

        doc.processing_status = status
        if error_message is not None:
            doc.error_message = error_message
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        if page_count is not None:
            doc.page_count = page_count
        if status in ("ready", "failed"):
            doc.processed_at = datetime.now(timezone.utc)

        await self.db.flush()
        return doc

    # =========================================================================
    # Delete
    # =========================================================================

    async def delete(self, document_id: uuid.UUID) -> bool:
        """
        Delete a document record.

        Returns True if deleted, False if not found.
        """
        doc = await self.get_by_id(document_id)
        if doc is None:
            return False
        await self.db.delete(doc)
        await self.db.flush()
        logger.debug("Document deleted: id=%s", document_id)
        return True

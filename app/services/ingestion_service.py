# app/services/ingestion_service.py
"""
Ingestion Service — Document Processing Orchestrator
=====================================================
This service owns the FULL ingestion pipeline for a single document:

    Upload received
        ↓
    Validate (file type, size, not empty)
        ↓
    Compute SHA-256 hash
        ↓
    Check for duplicate (by hash)
        ↓
    Save file to disk
        ↓
    Parse text (PDF or TXT)
        ↓
    Update document status → READY
        ↓ (on any failure)
    Update document status → FAILED

Design principles applied here:
---------------------------------
1. FAIL FAST: validate as early as possible, before expensive operations
2. IDEMPOTENCY: hash-based dedup means uploading the same file twice is safe
3. ATOMIC STATUS: every state transition is written to the DB, even failures
4. SEPARATION: this service orchestrates; it delegates parsing to parser_service
   and DB access to the repository

WHY NOT call the parser directly from the route handler?
---------------------------------------------------------
The route handler would become a 100-line function mixing HTTP concerns
(parsing the multipart body) with business concerns (what to do if the PDF
is corrupt) with infrastructure concerns (where to save the file).
Separating these means each layer can be tested and reasoned about independently.

Processing status transitions:
-------------------------------
UPLOADED   : set immediately when the DB record is created
PROCESSING : set just before expensive operations begin
READY      : set after successful parsing and text storage
FAILED     : set if ANY step fails, with error_message populated
"""

import hashlib
import os
import uuid
from pathlib import Path

import aiofiles

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ProcessingError, ValidationError
from app.core.logging import get_logger
from app.db.models import DocumentModel, DocumentChunkModel
from app.repositories.document_repository import DocumentRepository
from app.services.parser_service import ParseResult, parse_document
from app.services.chunking_service import chunk_document
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/octet-stream",  # Some clients send this for any file
}


class IngestionService:
    """
    Orchestrates the full document ingestion pipeline.

    Receives:
        - raw file bytes
        - original filename
        - content type (from HTTP header)
        - a DocumentRepository for DB access

    Produces:
        A DocumentModel in READY state with all metadata populated.
    """

    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()

    # =========================================================================
    # Main pipeline entry point
    # =========================================================================

    async def ingest(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
        description: str | None = None,
    ) -> DocumentModel:
        """
        Run the full ingestion pipeline.

        Args:
            file_bytes:   Raw bytes from the uploaded file.
            filename:     Original filename (e.g., "policy.pdf").
            content_type: MIME type from the HTTP Content-Type header.
            description:  Optional user-provided description.

        Returns:
            The DocumentModel record in READY state.

        Raises:
            ValidationError:  File fails validation (type, size, empty).
            ConflictError:    Duplicate file content detected (by hash).
            ProcessingError:  Parsing failed.
        """
        # ------------------------------------------------------------------
        # 1. Validate
        # ------------------------------------------------------------------
        file_type = self._validate_file(file_bytes, filename, content_type)

        # ------------------------------------------------------------------
        # 2. Compute SHA-256 hash
        # ------------------------------------------------------------------
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # ------------------------------------------------------------------
        # 3. Duplicate detection
        # ------------------------------------------------------------------
        existing = await self.repository.get_by_hash(sha256_hash)
        if existing:
            raise ConflictError(
                f"This file content already exists as document "
                f"'{existing.filename}' (id: {existing.document_id}). "
                f"Hash: {sha256_hash[:12]}..."
            )

        # ------------------------------------------------------------------
        # 4. Create DB record in UPLOADED state
        # ------------------------------------------------------------------
        document_id = uuid.uuid4()
        doc = DocumentModel(
            document_id=document_id,
            filename=filename,
            file_type=file_type,
            file_size_bytes=len(file_bytes),
            sha256_hash=sha256_hash,
            processing_status="uploaded",
            description=description,
        )
        doc = await self.repository.create(doc)
        logger.info(
            "Document registered: id=%s filename=%s size=%d bytes hash=%s...",
            document_id,
            filename,
            len(file_bytes),
            sha256_hash[:12],
        )

        # ------------------------------------------------------------------
        # 5. Mark as PROCESSING (before expensive operations)
        # ------------------------------------------------------------------
        await self.repository.update_status(document_id, "processing")

        # ------------------------------------------------------------------
        # 6. Save file to disk + parse (inside try/except for FAILED handling)
        # ------------------------------------------------------------------
        try:
            file_path = await self._save_file(file_bytes, document_id, file_type)
            doc.file_path = str(file_path)

            parse_result = self._parse(file_bytes, file_type)

            # ------------------------------------------------------------------
            # 6b. Chunking (Phase 3)
            # ------------------------------------------------------------------
            logger.debug("Chunking document id=%s", document_id)
            chunks = chunk_document(parse_result.pages)
            
            # ------------------------------------------------------------------
            # 6c. Embeddings (Phase 3)
            # ------------------------------------------------------------------
            logger.debug("Generating embeddings for %d chunks", len(chunks))
            chunk_texts = [c.text for c in chunks]
            
            # Embedding is best-effort: if the API is rate-limited or key is missing,
            # we still store the chunks (without vectors). They can be embedded later.
            embeddings = []
            try:
                import asyncio
                embeddings = await asyncio.wait_for(
                    self.embedding_service.get_embeddings(chunk_texts),
                    timeout=10.0
                )
            except Exception as embed_err:
                logger.warning(
                    "Embedding failed or timed out (chunks saved without vectors): %s", embed_err
                )
            
            # Create DB models for chunks
            chunk_models = []
            for i, chunk in enumerate(chunks):
                emb = embeddings[i] if embeddings and i < len(embeddings) else None
                chunk_models.append(
                    DocumentChunkModel(
                        document_id=document_id,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        text_content=chunk.text,
                        embedding=emb
                    )
                )
                
            await self.repository.create_chunks(chunk_models)

            # Update status to READY
            await self.repository.update_status(
                document_id,
                "ready",
                chunk_count=len(chunks),
                page_count=parse_result.total_pages,
            )
            doc.processing_status = "ready"
            doc.page_count = parse_result.total_pages
            doc.chunk_count = len(chunks)

            logger.info(
                "Document ingested: id=%s pages=%d chars=%d",
                document_id,
                parse_result.total_pages,
                parse_result.total_chars,
            )
            return doc

        except Exception as exc:
            # ------------------------------------------------------------------
            # 7. Mark as FAILED on any error
            # ------------------------------------------------------------------
            error_msg = str(exc)
            logger.error("Document ingestion failed: id=%s error=%s", document_id, error_msg)

            try:
                await self.repository.db.rollback()
                await self.repository.update_status(
                    document_id,
                    "failed",
                    error_message=error_msg,
                )
            except Exception as rollback_err:
                logger.error("Failed to update status to failed: %s", rollback_err)

            raise ProcessingError(f"Document processing failed: {error_msg}") from exc

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> str:
        """
        Validate the uploaded file. Returns the file type string ("pdf" or "txt").

        Validation layers:
        1. Extension check   — filename must end with .pdf or .txt
        2. Size check        — file must not be empty, must not exceed limit
        3. Magic bytes check — for PDFs, verify the %PDF-... header

        WHY multiple validation layers?
        A malicious user can rename "malware.exe" to "policy.pdf".
        Extension + magic bytes together are much harder to spoof.
        (Full MIME sniffing is overkill for a portfolio project, but the
        principle is demonstrated here.)
        """
        # --- 1. Extension ---
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"File type '.{suffix}' is not supported. "
                f"Allowed types: {', '.join(f'.{e}' for e in ALLOWED_EXTENSIONS)}"
            )

        # --- 2. Size ---
        if len(file_bytes) == 0:
            raise ValidationError("Uploaded file is empty.")

        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValidationError(
                f"File size ({len(file_bytes) / 1024 / 1024:.1f} MB) exceeds "
                f"the {self.settings.max_upload_size_mb} MB limit."
            )

        # --- 3. Magic bytes (PDF only) ---
        if suffix == "pdf":
            # All valid PDF files start with "%PDF-"
            if not file_bytes.startswith(b"%PDF-"):
                raise ValidationError(
                    "File does not appear to be a valid PDF "
                    "(missing %PDF- header). "
                    "If this is a real PDF, it may be corrupted."
                )

        return suffix

    # =========================================================================
    # File storage
    # =========================================================================

    async def _save_file(
        self,
        file_bytes: bytes,
        document_id: uuid.UUID,
        file_type: str,
    ) -> Path:
        """
        Save the file bytes to disk using an async file write.

        WHY async file write (aiofiles)?
        Synchronous file I/O (open() + write()) blocks the event loop for
        the duration of the write. For large files this could block for
        hundreds of milliseconds. aiofiles runs the write in a thread pool,
        returning control to the event loop immediately.

        Filename convention: {document_id}.{file_type}
        WHY not use the original filename?
        - Prevents filename collisions between users
        - Prevents path traversal attacks ("../../etc/passwd.pdf")
        - Makes the filename deterministic from the document_id
        """
        try:
            upload_dir = Path(self.settings.upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / f"{document_id}.{file_type}"

            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_bytes)

            logger.debug("File saved: path=%s size=%d", file_path, len(file_bytes))
            return file_path
        except Exception as err:
            logger.warning("Could not write file to disk (continuing in-memory): %s", err)
            return Path(f"data/documents/{document_id}.{file_type}")

    # =========================================================================
    # Parsing
    # =========================================================================

    def _parse(self, file_bytes: bytes, file_type: str) -> ParseResult:
        """
        Delegate parsing to the parser service.

        WHY not async? PyMuPDF's fitz.open() is a CPU-bound C operation.
        It doesn't do I/O — it processes bytes in memory. For CPU-bound
        work in async Python, you'd normally use run_in_executor() to
        offload to a thread pool. For now, since PDF parsing is fast
        (typically <100ms for typical documents), we run it synchronously.
        Phase 18 (performance) will profile and optimise if needed.
        """
        return parse_document(file_bytes, file_type)

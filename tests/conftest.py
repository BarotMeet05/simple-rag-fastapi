# tests/conftest.py
"""
Pytest Configuration and Shared Fixtures (Phase 2 update)
==========================================================
Phase 2 adds database-dependent tests. Strategy:

APPROACH: Mock the DB dependency for document endpoint tests
------------------------------------------------------------
We have two categories of tests:

1. Parser tests (test_parser_service.py)
   → Pure unit tests, no DB needed. Nothing changes.

2. Document endpoint tests (test_documents.py)
   → These now call routes that talk to PostgreSQL.

For endpoint tests in Phase 2, we use dependency overrides to inject a
mock document service. This means:
  - Tests don't require a running PostgreSQL
  - Tests run fast (no real I/O)
  - The test validates the HTTP layer (routing, validation, status codes)

Phase 4 will introduce integration tests that use a real test database.

Mock service approach:
----------------------
We create MockDocumentService — an in-memory implementation of the same
interface as the real DocumentService. The route handlers don't know or
care that they're talking to a mock.

This is the dependency injection pattern paying off: same interface,
swappable implementation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.documents import get_document_service
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    FileType,
    ProcessingStatus,
)
from app.core.exceptions import ConflictError, NotFoundError


# =============================================================================
# Mock Document Service
# =============================================================================


class MockDocumentService:
    """
    In-memory implementation of the DocumentService interface.

    Used in tests to avoid a real database.
    Mirrors the interface of app.services.document_service.DocumentService.
    """

    def __init__(self) -> None:
        self._store: dict[str, DocumentResponse] = {}
        self._hash_index: dict[str, str] = {}  # filename → document_id (simplified)

    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
        description: str | None = None,
    ) -> DocumentResponse:
        """Simulate ingestion with basic validation."""
        from pathlib import Path

        # Basic validation
        if not file_bytes:
            from app.core.exceptions import ValidationError as AppValidationError
            raise AppValidationError("Uploaded file is empty.")

        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix not in ("pdf", "txt"):
            from app.core.exceptions import ValidationError
            raise ValidationError(f"Unsupported file type: .{suffix}")

        # Duplicate detection (by filename, simplified for tests)
        if filename in self._hash_index:
            existing_id = self._hash_index[filename]
            raise ConflictError(
                f"A document with filename '{filename}' already exists "
                f"(document_id: {existing_id})"
            )

        # Corrupt PDF detection
        if suffix == "pdf" and not file_bytes.startswith(b"%PDF-"):
            from app.core.exceptions import ProcessingError
            raise ProcessingError("File does not appear to be a valid PDF")

        doc_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        doc = DocumentResponse(
            document_id=doc_id,
            filename=filename,
            file_type=FileType(suffix),
            file_size_bytes=len(file_bytes),
            processing_status=ProcessingStatus.READY,
            description=description,
            uploaded_at=now,
            chunk_count=0,
            page_count=1,
            error_message=None,
        )

        self._store[str(doc_id)] = doc
        self._hash_index[filename] = str(doc_id)
        return doc

    async def list_documents(self) -> DocumentListResponse:
        docs = sorted(self._store.values(), key=lambda d: d.uploaded_at, reverse=True)
        return DocumentListResponse(documents=list(docs), total=len(docs))

    async def get_document(self, document_id: uuid.UUID) -> DocumentResponse:
        doc = self._store.get(str(document_id))
        if doc is None:
            raise NotFoundError(f"Document '{document_id}' not found.")
        return doc

    async def delete_document(self, document_id: uuid.UUID) -> None:
        doc = self._store.get(str(document_id))
        if doc is None:
            raise NotFoundError(f"Document '{document_id}' not found.")
        # Remove from hash index
        self._hash_index.pop(doc.filename, None)
        del self._store[str(document_id)]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_document_service() -> MockDocumentService:
    """Fresh MockDocumentService per test."""
    return MockDocumentService()


@pytest.fixture
def client_with_mock_service(mock_document_service: MockDocumentService) -> TestClient:
    """
    TestClient with the real DB dependency replaced by MockDocumentService.
    Override is cleaned up after each test.
    """
    app.dependency_overrides[get_document_service] = lambda: mock_document_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped client (no DB dependency override — for health tests)."""
    return TestClient(app)

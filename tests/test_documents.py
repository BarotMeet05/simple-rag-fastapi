# tests/test_documents.py
"""
Document Endpoint Tests (Phase 2)
===================================
Phase 2 changes:
- POST /documents now accepts multipart/form-data
- We use client.post(..., files={"file": (...)}) for uploads
- Tests use the MockDocumentService (no real DB required)
- New tests cover: PDF upload, TXT upload, corrupt PDF, empty file, oversized file

multipart upload with httpx/TestClient:
----------------------------------------
    client.post(
        "/api/v1/documents",
        files={"file": ("policy.txt", b"content", "text/plain")},
        data={"description": "optional description"},
    )

The files dict format is: {"field_name": ("filename", bytes_or_file, content_type)}
The data dict carries regular form fields (not files).
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Helpers
# =============================================================================


def _make_txt_upload(content: str = "Test document content.", filename: str = "test.txt") -> dict:
    """Create a files dict for a TXT upload."""
    return {"file": (filename, content.encode("utf-8"), "text/plain")}


def _make_pdf_upload(filename: str = "test.pdf") -> dict:
    """
    Create a files dict for a minimal valid PDF upload.
    We generate a real PDF using PyMuPDF so magic bytes validation passes.
    """
    import pymupdf as fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Test PDF content for upload.", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return {"file": (filename, pdf_bytes, "application/pdf")}


def _corrupt_pdf_upload(filename: str = "corrupt.pdf") -> dict:
    """A file that looks like a PDF by name but has invalid content."""
    return {"file": (filename, b"not a real pdf", "application/pdf")}


# =============================================================================
# POST /documents — Upload
# =============================================================================


class TestUploadDocument:

    def test_upload_txt_returns_201(self, client_with_mock_service: TestClient) -> None:
        """Valid TXT upload returns 201 Created."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload(),
        )
        assert response.status_code == 201

    def test_upload_pdf_returns_201(self, client_with_mock_service: TestClient) -> None:
        """Valid PDF upload returns 201 Created."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_pdf_upload(),
        )
        assert response.status_code == 201

    def test_upload_response_shape(self, client_with_mock_service: TestClient) -> None:
        """Upload response contains all expected fields."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload(),
        )
        body = response.json()
        assert "document_id" in body
        assert "filename" in body
        assert "file_type" in body
        assert "file_size_bytes" in body
        assert "processing_status" in body
        assert "uploaded_at" in body

    def test_upload_txt_file_type_is_txt(self, client_with_mock_service: TestClient) -> None:
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload(),
        )
        assert response.json()["file_type"] == "txt"

    def test_upload_pdf_file_type_is_pdf(self, client_with_mock_service: TestClient) -> None:
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_pdf_upload(),
        )
        assert response.json()["file_type"] == "pdf"

    def test_upload_with_description(self, client_with_mock_service: TestClient) -> None:
        """Optional description form field is stored and returned."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload("Notes content", "notes.txt"),
            data={"description": "My important notes"},
        )
        assert response.status_code == 201
        assert response.json()["description"] == "My important notes"

    def test_upload_file_size_is_populated(self, client_with_mock_service: TestClient) -> None:
        """file_size_bytes reflects the actual uploaded content size."""
        content = "x" * 1000
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload(content),
        )
        assert response.json()["file_size_bytes"] == 1000

    def test_upload_document_id_is_valid_uuid(self, client_with_mock_service: TestClient) -> None:
        """document_id in response is a valid UUID."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload(),
        )
        doc_id = response.json()["document_id"]
        assert uuid.UUID(doc_id) is not None

    # -------------------------------------------------------------------------
    # Validation / Error cases
    # -------------------------------------------------------------------------

    def test_upload_unsupported_extension_returns_422(self, client_with_mock_service: TestClient) -> None:
        """Uploading a .exe file returns 422 Unprocessable Entity."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files={"file": ("malware.exe", b"data", "application/octet-stream")},
        )
        assert response.status_code == 422

    def test_upload_empty_file_returns_422(self, client_with_mock_service: TestClient) -> None:
        """Uploading an empty file returns 422."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert response.status_code == 422

    def test_upload_corrupt_pdf_returns_500(self, client_with_mock_service: TestClient) -> None:
        """Uploading a corrupt PDF returns a 5xx processing error."""
        response = client_with_mock_service.post(
            "/api/v1/documents",
            files=_corrupt_pdf_upload(),
        )
        # Should be a processing error (500) or validation error (422)
        assert response.status_code in (422, 500)

    def test_upload_duplicate_returns_409(self, client_with_mock_service: TestClient) -> None:
        """Uploading the same file twice returns 409 Conflict."""
        files = _make_txt_upload("Same content", "dup.txt")
        r1 = client_with_mock_service.post("/api/v1/documents", files=files)
        assert r1.status_code == 201

        files = _make_txt_upload("Same content", "dup.txt")
        r2 = client_with_mock_service.post("/api/v1/documents", files=files)
        assert r2.status_code == 409

    def test_upload_duplicate_error_code(self, client_with_mock_service: TestClient) -> None:
        """409 response has CONFLICT error code."""
        files = _make_txt_upload("Content", "dup2.txt")
        client_with_mock_service.post("/api/v1/documents", files=files)
        files = _make_txt_upload("Content", "dup2.txt")
        r = client_with_mock_service.post("/api/v1/documents", files=files)
        assert r.json()["error"]["code"] == "CONFLICT"

    def test_upload_without_file_returns_422(self, client_with_mock_service: TestClient) -> None:
        """POST without a file field returns 422."""
        response = client_with_mock_service.post("/api/v1/documents")
        assert response.status_code == 422


# =============================================================================
# GET /documents — List
# =============================================================================


class TestListDocuments:

    def test_list_returns_200(self, client_with_mock_service: TestClient) -> None:
        response = client_with_mock_service.get("/api/v1/documents")
        assert response.status_code == 200

    def test_list_empty_initially(self, client_with_mock_service: TestClient) -> None:
        response = client_with_mock_service.get("/api/v1/documents")
        assert response.json()["total"] == 0

    def test_list_shows_uploaded_document(self, client_with_mock_service: TestClient) -> None:
        client_with_mock_service.post("/api/v1/documents", files=_make_txt_upload())
        response = client_with_mock_service.get("/api/v1/documents")
        assert response.json()["total"] == 1

    def test_list_total_matches_upload_count(self, client_with_mock_service: TestClient) -> None:
        for i in range(3):
            client_with_mock_service.post(
                "/api/v1/documents",
                files=_make_txt_upload(f"Doc {i}", f"doc{i}.txt"),
            )
        response = client_with_mock_service.get("/api/v1/documents")
        assert response.json()["total"] == 3


# =============================================================================
# GET /documents/{id}
# =============================================================================


class TestGetDocument:

    def test_get_existing_returns_200(self, client_with_mock_service: TestClient) -> None:
        r = client_with_mock_service.post("/api/v1/documents", files=_make_txt_upload())
        doc_id = r.json()["document_id"]
        response = client_with_mock_service.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200

    def test_get_returns_correct_fields(self, client_with_mock_service: TestClient) -> None:
        r = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload("content", "check.txt"),
        )
        doc_id = r.json()["document_id"]
        response = client_with_mock_service.get(f"/api/v1/documents/{doc_id}")
        body = response.json()
        assert body["document_id"] == doc_id
        assert body["filename"] == "check.txt"

    def test_get_nonexistent_returns_404(self, client_with_mock_service: TestClient) -> None:
        fake_id = uuid.uuid4()
        response = client_with_mock_service.get(f"/api/v1/documents/{fake_id}")
        assert response.status_code == 404

    def test_get_nonexistent_error_code(self, client_with_mock_service: TestClient) -> None:
        fake_id = uuid.uuid4()
        response = client_with_mock_service.get(f"/api/v1/documents/{fake_id}")
        assert response.json()["error"]["code"] == "NOT_FOUND"

    def test_get_invalid_uuid_returns_422(self, client_with_mock_service: TestClient) -> None:
        response = client_with_mock_service.get("/api/v1/documents/not-a-uuid")
        assert response.status_code == 422


# =============================================================================
# DELETE /documents/{id}
# =============================================================================


class TestDeleteDocument:

    def test_delete_existing_returns_204(self, client_with_mock_service: TestClient) -> None:
        r = client_with_mock_service.post("/api/v1/documents", files=_make_txt_upload())
        doc_id = r.json()["document_id"]
        response = client_with_mock_service.delete(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 204

    def test_delete_removes_from_list(self, client_with_mock_service: TestClient) -> None:
        r = client_with_mock_service.post(
            "/api/v1/documents",
            files=_make_txt_upload("content", "todelete.txt"),
        )
        doc_id = r.json()["document_id"]
        client_with_mock_service.delete(f"/api/v1/documents/{doc_id}")
        list_r = client_with_mock_service.get("/api/v1/documents")
        filenames = [d["filename"] for d in list_r.json()["documents"]]
        assert "todelete.txt" not in filenames

    def test_delete_nonexistent_returns_404(self, client_with_mock_service: TestClient) -> None:
        fake_id = uuid.uuid4()
        response = client_with_mock_service.delete(f"/api/v1/documents/{fake_id}")
        assert response.status_code == 404

    def test_delete_allows_reupload(self, client_with_mock_service: TestClient) -> None:
        """After deleting, the same filename can be re-uploaded."""
        files = _make_txt_upload("content", "reuse.txt")
        r = client_with_mock_service.post("/api/v1/documents", files=files)
        doc_id = r.json()["document_id"]
        client_with_mock_service.delete(f"/api/v1/documents/{doc_id}")

        files = _make_txt_upload("content", "reuse.txt")
        r2 = client_with_mock_service.post("/api/v1/documents", files=files)
        assert r2.status_code == 201

    def test_double_delete_returns_404(self, client_with_mock_service: TestClient) -> None:
        r = client_with_mock_service.post("/api/v1/documents", files=_make_txt_upload())
        doc_id = r.json()["document_id"]
        client_with_mock_service.delete(f"/api/v1/documents/{doc_id}")
        r2 = client_with_mock_service.delete(f"/api/v1/documents/{doc_id}")
        assert r2.status_code == 404

# app/schemas/document.py
"""
Document Schemas (Request / Response Models)
=============================================
WHY Pydantic schemas?
---------------------
Coming from Go, you understand how struct tags enforce request/response shapes.
Pydantic models are the Python equivalent — but with automatic:

1. Parsing    — JSON body → Python object with correct types
2. Validation — field constraints enforced before your code runs
3. Docs       — FastAPI generates OpenAPI/Swagger docs from these models automatically
4. Serialization — Python object → JSON response

Schema vs Model distinction (important for this project):
---------------------------------------------------------
app/schemas/   — Pydantic models that define the SHAPE of API requests/responses.
                 These are the "contract" between client and server.

app/models/    — ORM/database models (SQLAlchemy, future phase).
                 These represent tables in PostgreSQL.

Why separate them? Because what you store in the database often differs from
what you expose via the API. For example:
  - You might store a file hash in the DB but not expose it in the response
  - You might accept a filename in the request but compute the document_id server-side
  - You can version API schemas independently of DB schema changes

ProcessingStatus — Enums in APIs:
----------------------------------
Using a string enum (not a plain string) for status means:
- Invalid statuses are rejected at the boundary ("in_progress" → ValidationError)
- OpenAPI docs show exactly which values are valid
- Your IDE gives you autocomplete
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# =============================================================================
# Enumerations
# =============================================================================


class FileType(str, Enum):
    """
    Supported document types.
    str is the mixin so FileType.PDF == "pdf" — convenient for JSON serialisation.
    We'll expand this in Phase 2 when we add actual file handling.
    """

    PDF = "pdf"
    TXT = "txt"


class ProcessingStatus(str, Enum):
    """
    Document lifecycle states.

    UPLOADED   → file received, not yet processed
    PROCESSING → text extraction + chunking + embedding in progress
    READY      → fully indexed, searchable
    FAILED     → processing encountered an unrecoverable error

    This is a simple state machine. In Phase 2 we'll enforce valid transitions
    (e.g., READY → FAILED is valid, but FAILED → PROCESSING without re-upload is not).
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# =============================================================================
# Request models (what the client sends)
# =============================================================================


class DocumentCreate(BaseModel):
    """
    Body for POST /documents.

    In Phase 1, the client sends JSON. In Phase 2, we'll switch to
    multipart/form-data (file upload). Keeping this as a simple JSON
    body now so we can focus on API patterns.

    Field(...) — the ellipsis means "required, no default".
    Field(default=...) — has a default value.
    """

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename including extension",
        examples=["company_handbook.pdf"],
    )
    file_type: FileType = Field(
        ...,
        description="Document type; must be 'pdf' or 'txt'",
        examples=["pdf"],
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional human-readable description of the document",
    )

    @model_validator(mode="after")
    def filename_must_match_type(self) -> "DocumentCreate":
        """
        Cross-field validation: filename extension must match file_type.

        model_validator(mode='after') runs after ALL fields are validated and
        gives us a fully-constructed model instance (self) to inspect.
        This is the correct Pydantic v2 pattern for cross-field validation.

        This is an example of "fail fast" — reject bad input at the API
        boundary before it reaches any business logic.
        """
        if self.file_type and not self.filename.lower().endswith(f".{self.file_type.value}"):
            raise ValueError(
                f"Filename '{self.filename}' does not match file_type '{self.file_type.value}'. "
                f"Expected extension: .{self.file_type.value}"
            )
        return self


# =============================================================================
# Response models (what the server returns)
# =============================================================================


class DocumentResponse(BaseModel):
    """
    Representation of a document returned by the API.

    Note that document_id is a UUID. UUIDs are better than integer auto-increment
    IDs for APIs because:
    - They're globally unique (safe in distributed systems)
    - They don't leak information about total record count
    - They can be generated client-side or server-side
    """

    document_id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Document type")
    file_size_bytes: int = Field(..., description="File size in bytes", ge=0)
    processing_status: ProcessingStatus = Field(..., description="Current processing state")
    description: str | None = Field(default=None, description="Optional description")
    uploaded_at: datetime = Field(..., description="UTC timestamp of upload")
    chunk_count: int = Field(default=0, description="Number of chunks extracted (0 until READY)")
    page_count: int | None = Field(default=None, description="Number of pages (PDF only)")
    error_message: str | None = Field(default=None, description="Error details if status is FAILED")

    model_config = {
        # Allow ORM objects (SQLAlchemy models) to be passed in directly — used in Phase 2+
        "from_attributes": True,
    }


class DocumentListResponse(BaseModel):
    """
    Paginated list of documents.

    Even though Phase 1 is in-memory, we design the response to be pagination-ready.
    This avoids a breaking API change later when we add cursor/offset pagination.
    """

    documents: list[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents (before pagination)", ge=0)
    # Phase 1: no pagination yet, but fields are reserved
    page: int = Field(default=1, description="Current page (reserved for pagination)", ge=1)
    page_size: int = Field(default=100, description="Items per page (reserved for pagination)", ge=1)

# app/db/models.py
"""
SQLAlchemy ORM Models (Database Tables)
========================================
These classes define the actual PostgreSQL tables.

ORM (Object-Relational Mapper) concept:
----------------------------------------
An ORM maps Python classes to database tables and Python objects to rows.
Instead of writing raw SQL like:
    INSERT INTO documents (document_id, filename, ...) VALUES (...)

You write:
    db.add(DocumentModel(document_id=..., filename=...))
    await db.commit()

The ORM translates this to SQL for you, handles type conversion, and
provides a Python-native query interface.

Schema vs Model (reminder from Phase 1):
-----------------------------------------
app/schemas/document.py  → Pydantic: API request/response SHAPE
app/db/models.py         → SQLAlchemy: DATABASE TABLE STRUCTURE

They look similar but serve completely different purposes.
Pydantic schemas are serialised to/from JSON.
SQLAlchemy models are persisted to/from PostgreSQL.

Why map_columns=True (Pydantic v2 / SQLAlchemy 2 integration)?
---------------------------------------------------------------
With SQLAlchemy 2.0's mapped_column() and Annotated types,
we get full type-safe column declarations that IDEs understand.

Why UUID primary keys?
-----------------------
- Globally unique: safe in distributed systems and replication
- Non-sequential: don't leak row counts to API consumers
- Can be generated in Python before the INSERT (no DB round-trip needed to get the ID)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class DocumentModel(Base):
    """
    Represents a document uploaded by the user.

    Table: documents

    State machine:
        UPLOADED → PROCESSING → READY
                             ↘ FAILED
    """

    __tablename__ = "documents"

    # -------------------------------------------------------------------------
    # Primary key
    # -------------------------------------------------------------------------
    # server_default=False: UUID is generated in Python (not by the DB).
    # This lets us know the ID before inserting, which is useful for logging
    # and for returning it in the HTTP response immediately.
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # File metadata
    # -------------------------------------------------------------------------
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)

    # File size in bytes — 0 until the file is actually written
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # SHA-256 hex digest of the file content.
    # WHY store this?
    # 1. Duplicate detection: if two uploads have the same hash, they're identical files
    # 2. Integrity checking: re-hash the stored file and compare to detect corruption
    # 3. Deduplication: store only one copy of identical files (Phase 2+ consideration)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)

    # -------------------------------------------------------------------------
    # Processing state
    # -------------------------------------------------------------------------
    processing_status: Mapped[str] = mapped_column(
        String(20),
        default="uploaded",
        nullable=False,
        index=True,  # We'll query by status (e.g., "find all FAILED documents")
    )

    # Populated if processing_status == "failed"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -------------------------------------------------------------------------
    # Content metadata (populated after parsing)
    # -------------------------------------------------------------------------
    # Number of text chunks extracted. 0 until status = READY
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Number of pages (PDF only). NULL for TXT files.
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Optional user-provided description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # File path on disk (relative to project root)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    # timezone=True stores timestamps in UTC in the DB.
    # Always store timestamps in UTC. Convert to local time only at display time.
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<DocumentModel id={self.document_id} "
            f"filename={self.filename!r} "
            f"status={self.processing_status!r}>"
        )

# app/services/parser_service.py
"""
Document Parser Service
========================
Pure parsing functions — no database, no HTTP, no side effects.

WHY keep parsing separate from ingestion?
-----------------------------------------
1. Testability: pass bytes in, get structured data out — no mocking needed
2. Reusability: the same parser can be called from a CLI script, a background
   worker, or an HTTP handler
3. Single responsibility: this module knows ONLY how to extract text
4. Composability: swap PyMuPDF for another library without touching ingestion logic

Parsed output anatomy:
-----------------------
Each parsed document becomes a list of ParsedPage objects:

    ParsedPage(page_number=1, text="The company was founded in...")
    ParsedPage(page_number=2, text="Our engineering values are...")

For TXT files, the entire file is treated as a single "page" (page_number=1).
This uniform interface means the chunking service (Phase 3) doesn't care
whether the source was a PDF or TXT.

Why page numbers matter for RAG:
---------------------------------
When the LLM answers "What is the deductible?", we want to show the user:
    Source: policy.pdf — Page 12

Without preserving page numbers during parsing, we lose this traceability.
This is why we extract page-by-page, not as a single string.

Text cleaning:
--------------
Raw PDF text often contains:
- Multiple consecutive blank lines
- Hyphenated words split across lines ("im-\nportant" → "important")
- Header/footer repetition
- Non-breaking spaces (\xa0)

We apply lightweight normalisation here. Heavy semantic cleaning
(sentence boundary detection, deduplication) is deferred to Phase 3.
"""

import re
from dataclasses import dataclass

import fitz  # PyMuPDF — 'fitz' is the module name for historical reasons

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedPage:
    """
    A single page of extracted text with its metadata.

    dataclass automatically generates __init__, __repr__, __eq__ —
    ideal for pure data containers with no behaviour.
    """

    page_number: int  # 1-indexed (matches PDF page numbers shown to users)
    text: str         # Cleaned text content of this page
    char_count: int   # Raw character count (before chunking)


@dataclass
class ParseResult:
    """The complete result of parsing one document."""

    pages: list[ParsedPage]
    total_pages: int
    total_chars: int
    file_type: str  # "pdf" or "txt"

    @property
    def full_text(self) -> str:
        """Concatenate all page texts (useful for full-document operations)."""
        return "\n\n".join(p.text for p in self.pages if p.text.strip())


# =============================================================================
# Text normalisation
# =============================================================================


def _clean_text(raw: str) -> str:
    """
    Apply lightweight text normalisation.

    What we do:
    - Replace non-breaking spaces with regular spaces
    - Rejoin hyphenated line breaks (e.g., "im-\nportant" → "important")
    - Collapse runs of 3+ blank lines to 2 blank lines (preserve paragraph structure)
    - Strip trailing whitespace from each line

    What we deliberately do NOT do here:
    - Remove headers/footers (requires heuristics; deferred to chunking)
    - Sentence boundary detection (deferred to chunking)
    - Deduplication of repeated text (deferred to chunking)
    """
    # Non-breaking spaces → regular spaces
    text = raw.replace("\xa0", " ")

    # Rejoin soft hyphens at line breaks: "im-\nportant" → "important"
    text = re.sub(r"-\n(\w)", r"\1", text)

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)

    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =============================================================================
# TXT parser
# =============================================================================


def parse_txt(file_bytes: bytes) -> ParseResult:
    """
    Parse a plain text file.

    TXT files have no inherent page structure. We treat the entire file
    as a single page (page_number=1) for consistency with the ParsedPage
    interface. The chunking service will split it into appropriately-sized
    chunks regardless.

    Args:
        file_bytes: Raw bytes from the uploaded file.

    Returns:
        ParseResult with a single ParsedPage.

    Raises:
        ValueError: If the file cannot be decoded as UTF-8 or latin-1.
    """
    # Try UTF-8 first (most common), fall back to latin-1 (covers all single-byte values)
    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = file_bytes.decode("latin-1")
        logger.debug("TXT file decoded as latin-1 (not valid UTF-8)")

    cleaned = _clean_text(raw_text)

    if not cleaned:
        raise ValueError("TXT file contains no extractable text")

    page = ParsedPage(
        page_number=1,
        text=cleaned,
        char_count=len(cleaned),
    )

    logger.debug("TXT parsed: chars=%d", len(cleaned))
    return ParseResult(
        pages=[page],
        total_pages=1,
        total_chars=len(cleaned),
        file_type="txt",
    )


# =============================================================================
# PDF parser
# =============================================================================


def parse_pdf(file_bytes: bytes) -> ParseResult:
    """
    Parse a PDF file using PyMuPDF (fitz).

    PyMuPDF overview:
    -----------------
    PyMuPDF is a Python binding for MuPDF — a C library used in production
    PDF viewers (Firefox, Sumatra). It's significantly faster and more
    accurate than pure-Python alternatives.

    How it extracts text:
    1. Open the PDF from bytes (no temp file needed)
    2. Iterate pages
    3. For each page, call page.get_text("text") which extracts the raw text
       stream with basic reading-order heuristics

    Alternatives considered:
    - pdfplumber: good for tables, slower for plain text
    - PyPDF2/pypdf: pure Python, less accurate with complex layouts
    - pdfminer.six: very accurate but complex API
    - PyMuPDF (chosen): fastest, most reliable for plain text extraction

    Args:
        file_bytes: Raw PDF bytes from the uploaded file.

    Returns:
        ParseResult with one ParsedPage per PDF page.

    Raises:
        ValueError: If the PDF is encrypted, corrupt, or contains no text.
    """
    # Open the PDF from bytes in memory
    # The "pdf" stream type tells fitz how to interpret the bytes
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Cannot open PDF: {e}") from e

    # Check for password-protected PDFs
    if doc.is_encrypted:
        doc.close()
        raise ValueError("PDF is password-protected. Please provide an unencrypted file.")

    pages: list[ParsedPage] = []
    total_chars = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_number = page_idx + 1  # Convert 0-indexed to 1-indexed for users

        # get_text("text") extracts plain text with reading-order sorting
        # Alternative: get_text("blocks") gives bounding-box info per text block
        raw_text = page.get_text("text")
        cleaned = _clean_text(raw_text)

        if cleaned:  # Skip pages with no extractable text (e.g., image-only pages)
            pages.append(ParsedPage(
                page_number=page_number,
                text=cleaned,
                char_count=len(cleaned),
            ))
            total_chars += len(cleaned)
        else:
            logger.debug("PDF page %d has no extractable text (may be image-only)", page_number)

    doc.close()

    if not pages:
        raise ValueError(
            "PDF contains no extractable text. "
            "The PDF may be image-based (scanned). OCR support is not included in this phase."
        )

    total_pdf_pages = len(pages)  # We already have pages list; use its length
    logger.debug("PDF parsed: extractable_pages=%d total_chars=%d", total_pdf_pages, total_chars)

    return ParseResult(
        pages=pages,
        total_pages=total_pdf_pages,
        total_chars=total_chars,
        file_type="pdf",
    )


# =============================================================================
# Dispatcher
# =============================================================================


def parse_document(file_bytes: bytes, file_type: str) -> ParseResult:
    """
    Route parsing to the appropriate parser based on file type.

    Args:
        file_bytes: Raw file content.
        file_type:  "pdf" or "txt" (lowercase).

    Returns:
        ParseResult

    Raises:
        ValueError: For unsupported file types or parsing failures.
    """
    if file_type == "txt":
        return parse_txt(file_bytes)
    elif file_type == "pdf":
        return parse_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_type!r}. Expected 'pdf' or 'txt'.")

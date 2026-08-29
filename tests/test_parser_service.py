# tests/test_parser_service.py
"""
Parser Service Unit Tests
==========================
These tests are pure unit tests — no database, no HTTP, no filesystem.
We just pass bytes in and assert on the returned ParseResult.

This demonstrates the value of the pure parser service design:
tests are fast, simple, and require zero infrastructure.

Test strategy:
- TXT: valid content, empty file, different encodings
- PDF: we test with a programmatically generated minimal PDF
- Dispatcher: unsupported file type
"""

import pytest

from app.services.parser_service import ParseResult, ParsedPage, parse_document, parse_pdf, parse_txt


# =============================================================================
# TXT Parser tests
# =============================================================================


class TestParseTxt:

    def test_valid_txt_returns_parse_result(self) -> None:
        """A valid TXT file returns a ParseResult."""
        content = "This is a test document.\n\nIt has two paragraphs."
        result = parse_txt(content.encode("utf-8"))
        assert isinstance(result, ParseResult)

    def test_valid_txt_has_single_page(self) -> None:
        """TXT files always have exactly 1 page."""
        result = parse_txt(b"Hello world.")
        assert result.total_pages == 1
        assert len(result.pages) == 1

    def test_valid_txt_page_number_is_1(self) -> None:
        """The single page has page_number=1 (1-indexed)."""
        result = parse_txt(b"Hello world.")
        assert result.pages[0].page_number == 1

    def test_valid_txt_text_content(self) -> None:
        """Extracted text matches the file content."""
        content = "The answer is 42."
        result = parse_txt(content.encode("utf-8"))
        assert "The answer is 42." in result.pages[0].text

    def test_valid_txt_char_count(self) -> None:
        """char_count is populated and positive."""
        result = parse_txt(b"Hello world.")
        assert result.pages[0].char_count > 0
        assert result.total_chars > 0

    def test_txt_normalises_non_breaking_spaces(self) -> None:
        """Non-breaking spaces (\xa0) are replaced with regular spaces."""
        content = "word\xa0word"
        result = parse_txt(content.encode("utf-8"))
        assert "\xa0" not in result.pages[0].text
        assert "word word" in result.pages[0].text

    def test_txt_collapses_excessive_blank_lines(self) -> None:
        """More than 2 consecutive blank lines are collapsed."""
        content = "Para 1\n\n\n\n\nPara 2"
        result = parse_txt(content.encode("utf-8"))
        # Should not have 4+ consecutive newlines
        assert "\n\n\n\n" not in result.pages[0].text

    def test_empty_txt_raises_value_error(self) -> None:
        """An empty TXT file (after cleaning) raises ValueError."""
        with pytest.raises(ValueError, match="no extractable text"):
            parse_txt(b"")

    def test_whitespace_only_txt_raises_value_error(self) -> None:
        """A TXT file containing only whitespace raises ValueError."""
        with pytest.raises(ValueError, match="no extractable text"):
            parse_txt(b"   \n\n\t  \n  ")

    def test_latin1_encoded_txt(self) -> None:
        """TXT files encoded in latin-1 (not UTF-8) are handled gracefully."""
        # This byte is invalid UTF-8 but valid latin-1 (é)
        content = b"caf\xe9 au lait"
        result = parse_txt(content)
        assert result.total_pages == 1
        assert result.total_chars > 0

    def test_txt_file_type_is_txt(self) -> None:
        """ParseResult.file_type is 'txt'."""
        result = parse_txt(b"Hello.")
        assert result.file_type == "txt"

    def test_full_text_property(self) -> None:
        """ParseResult.full_text concatenates page texts."""
        result = parse_txt(b"Some content here.")
        assert len(result.full_text) > 0


# =============================================================================
# PDF Parser tests
# =============================================================================

def _make_minimal_pdf(text: str = "Test content for RAG.") -> bytes:
    """
    Create a minimal valid PDF in memory containing one page of text.

    We generate a synthetic PDF here instead of loading a file from disk.
    This makes the test self-contained and reproducible.

    A minimal PDF has:
    - A file header (%PDF-1.4)
    - Objects: catalog, pages, page, font, content stream
    - A cross-reference table
    - A trailer

    This is not meant to be educational — it's just test infrastructure.
    In production tests you'd use real sample PDFs.
    """
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size in points
    # Insert text at position (72, 100) — 1 inch from left, ~1.4 inches from top
    page.insert_text((72, 100), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestParsePdf:

    def test_valid_pdf_returns_parse_result(self) -> None:
        """A valid PDF returns a ParseResult."""
        pdf = _make_minimal_pdf("Policy coverage is $2 million.")
        result = parse_pdf(pdf)
        assert isinstance(result, ParseResult)

    def test_valid_pdf_has_pages(self) -> None:
        """A parsed PDF has at least one page."""
        pdf = _make_minimal_pdf()
        result = parse_pdf(pdf)
        assert result.total_pages >= 1
        assert len(result.pages) >= 1

    def test_valid_pdf_page_number_starts_at_1(self) -> None:
        """First page has page_number=1 (1-indexed)."""
        pdf = _make_minimal_pdf()
        result = parse_pdf(pdf)
        assert result.pages[0].page_number == 1

    def test_valid_pdf_text_extracted(self) -> None:
        """Text content is correctly extracted from the PDF."""
        pdf = _make_minimal_pdf("Deductible amount is $25,000.")
        result = parse_pdf(pdf)
        full = result.full_text
        assert "Deductible" in full or "deductible" in full.lower()

    def test_pdf_file_type_is_pdf(self) -> None:
        """ParseResult.file_type is 'pdf'."""
        pdf = _make_minimal_pdf()
        result = parse_pdf(pdf)
        assert result.file_type == "pdf"

    def test_invalid_bytes_raises_value_error(self) -> None:
        """Garbage bytes that are not a PDF raise ValueError."""
        with pytest.raises(ValueError, match="Cannot open PDF"):
            parse_pdf(b"this is not a pdf")

    def test_non_pdf_with_pdf_magic_raises_gracefully(self) -> None:
        """Truncated/corrupt PDF raises ValueError."""
        with pytest.raises(ValueError):
            parse_pdf(b"%PDF-1.4 corrupt data here %%%")

    def test_char_count_positive(self) -> None:
        """Parsed PDF has a positive character count."""
        pdf = _make_minimal_pdf("Some text on the page.")
        result = parse_pdf(pdf)
        assert result.total_chars > 0


# =============================================================================
# Dispatcher tests
# =============================================================================


class TestParseDocument:

    def test_dispatches_txt(self) -> None:
        """parse_document dispatches to parse_txt for 'txt'."""
        result = parse_document(b"Hello world.", "txt")
        assert result.file_type == "txt"

    def test_dispatches_pdf(self) -> None:
        """parse_document dispatches to parse_pdf for 'pdf'."""
        pdf = _make_minimal_pdf()
        result = parse_document(pdf, "pdf")
        assert result.file_type == "pdf"

    def test_unsupported_type_raises_value_error(self) -> None:
        """Unsupported file type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document(b"data", "docx")

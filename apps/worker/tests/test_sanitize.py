"""Regression tests for the NUL-byte bug: pypdf/python-docx/pandas+openpyxl
can embed \\x00 in extracted text, which Postgres rejects on insert
(`ValueError: A string literal cannot contain NUL (0x00) characters.`).
"""

from app.chunking.chunker import chunk_sections
from app.parsing.sanitize import sanitize_text
from app.parsing.types import ParsedSection


def test_sanitize_text_removes_nul_bytes():
    assert sanitize_text("Hello\x00World") == "HelloWorld"


def test_sanitize_text_removes_other_control_chars_but_keeps_whitespace():
    assert sanitize_text("a\x01\x02b\x7f") == "ab"
    assert sanitize_text("Keep\ttabs\nand\rnewlines") == "Keep\ttabs\nand\rnewlines"


def test_sanitize_text_handles_none():
    assert sanitize_text(None) is None


def test_chunk_sections_strips_nul_from_text_and_heading():
    sections = [
        ParsedSection(
            text="Line one\x00 with an embedded NUL byte.",
            heading="Head\x00ing",
            chunk_type="text",
        )
    ]

    drafts = chunk_sections(sections)

    assert len(drafts) == 1
    assert "\x00" not in drafts[0].text
    assert drafts[0].heading == "Heading"


def test_chunk_sections_strips_nul_from_non_text_chunk_types():
    sections = [ParsedSection(text="| a\x00 | b |", heading="Table\x00", chunk_type="table")]

    drafts = chunk_sections(sections)

    assert len(drafts) == 1
    assert drafts[0].chunk_type == "table"
    assert "\x00" not in drafts[0].text
    assert drafts[0].heading == "Table"


def test_chunk_sections_skips_section_that_is_only_nul_bytes():
    sections = [ParsedSection(text="\x00\x00\x00", chunk_type="text")]

    drafts = chunk_sections(sections)

    assert drafts == []

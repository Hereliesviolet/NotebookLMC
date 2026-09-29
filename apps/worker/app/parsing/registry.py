"""Dispatches to the right parser based on MIME type / file extension.

Supported MVP file types (architecture doc §14.1): PDF, DOCX, TXT, Markdown,
HTML, CSV, XLSX. PowerPoint/Audio/Video/OCR are documented as later
extensions (§14.2), not implemented here.
"""

from app.parsing.csv_xlsx import parse_csv, parse_xlsx
from app.parsing.docx import parse_docx
from app.parsing.html import parse_html
from app.parsing.pdf import parse_pdf
from app.parsing.txt_md import parse_markdown, parse_text
from app.parsing.types import ParsedSection

_MIME_PARSERS = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "text/plain": parse_text,
    "text/markdown": parse_markdown,
    "text/html": parse_html,
    "text/csv": parse_csv,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": parse_xlsx,
}

_EXTENSION_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".txt": parse_text,
    ".md": parse_markdown,
    ".markdown": parse_markdown,
    ".html": parse_html,
    ".htm": parse_html,
    ".csv": parse_csv,
    ".xlsx": parse_xlsx,
}


class UnsupportedFileTypeError(ValueError):
    pass


def parse_document(mime_type: str, filename: str, data: bytes) -> list[ParsedSection]:
    parser = _MIME_PARSERS.get(mime_type)
    if parser is None:
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        parser = _EXTENSION_PARSERS.get(suffix)
    if parser is None:
        raise UnsupportedFileTypeError(
            f"No parser registered for mime_type={mime_type!r} filename={filename!r}"
        )
    return parser(data)

"""PDF parsing (MVP choice: pypdf, see docs/architecture.md §14.4 recommendation).

Docling/Unstructured + OCR fallback are documented as a later upgrade path
for scanned/complex PDFs (architecture doc §14.2/§14.4).
"""
import io

from pypdf import PdfReader

from app.parsing.sanitize import sanitize_text
from app.parsing.types import ParsedSection


def parse_pdf(data: bytes) -> list[ParsedSection]:
    reader = PdfReader(io.BytesIO(data))
    sections: list[ParsedSection] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = sanitize_text(page.extract_text() or "").strip()
        if not text:
            continue
        sections.append(ParsedSection(text=text, page_start=page_index, page_end=page_index, chunk_type="text"))
    return sections

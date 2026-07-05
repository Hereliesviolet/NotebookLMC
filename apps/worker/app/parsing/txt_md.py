"""Plain text and Markdown parsing.

Markdown headings (`# `, `## `, ...) are used to split into sections so
chunking can attach a meaningful `heading` to each chunk.
"""
import re

from app.parsing.types import ParsedSection

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_text(data: bytes) -> list[ParsedSection]:
    text = data.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    return [ParsedSection(text=text, chunk_type="text")]


def parse_markdown(data: bytes) -> list[ParsedSection]:
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()

    sections: list[ParsedSection] = []
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append(ParsedSection(text=body, heading=current_heading, chunk_type="text"))
        buffer.clear()

    for line in lines:
        match = _HEADING_RE.match(line)
        if match:
            flush()
            current_heading = match.group(2).strip()
            continue
        buffer.append(line)
    flush()

    return sections or parse_text(data)

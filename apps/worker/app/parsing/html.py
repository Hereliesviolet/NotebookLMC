"""HTML parsing via BeautifulSoup."""

from bs4 import BeautifulSoup

from app.parsing.sanitize import sanitize_text
from app.parsing.types import ParsedSection

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def parse_html(data: bytes) -> list[ParsedSection]:
    soup = BeautifulSoup(data.decode("utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    sections: list[ParsedSection] = []
    current_heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        text = sanitize_text("\n".join(buffer)).strip()
        if text:
            sections.append(ParsedSection(text=text, heading=current_heading, chunk_type="text"))
        buffer.clear()

    body = soup.body or soup
    for element in body.find_all(True, recursive=True):
        if element.name in _HEADING_TAGS:
            flush()
            current_heading = sanitize_text(element.get_text(strip=True))
        elif element.name in {"p", "li"}:
            text = sanitize_text(element.get_text(strip=True))
            if text:
                buffer.append(text)
    flush()

    if not sections:
        text = sanitize_text(soup.get_text(separator="\n", strip=True))
        if text:
            sections.append(ParsedSection(text=text, chunk_type="text"))

    return sections

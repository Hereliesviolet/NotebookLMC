"""Chunking strategy.

Not blind fixed-length chunking: we chunk within the heading/section
structure already produced by parsing, and only apply a sliding window to
long text sections. Tables/slides/transcripts stay as their own chunk.

Target sizes (approximated with a word count - swap in a real tokenizer
later if exact token budgets become important):
  - text: 600-1200 tokens, ~150 token overlap -> approximated as
    450-900 words with ~110 word overlap
  - table/slide/transcript/image_caption: kept as a single chunk as-is
"""

from dataclasses import dataclass, field

from app.parsing.sanitize import sanitize_text
from app.parsing.types import ParsedSection

MIN_WORDS = 450
MAX_WORDS = 900
OVERLAP_WORDS = 110


@dataclass
class ChunkDraft:
    text: str
    chunk_type: str = "text"
    page_start: int | None = None
    page_end: int | None = None
    heading: str | None = None
    metadata: dict = field(default_factory=dict)


def _split_long_text(words: list[str]) -> list[list[str]]:
    if len(words) <= MAX_WORDS:
        return [words]

    windows: list[list[str]] = []
    start = 0
    step = MAX_WORDS - OVERLAP_WORDS
    while start < len(words):
        windows.append(words[start : start + MAX_WORDS])
        start += step
    return windows


def chunk_sections(sections: list[ParsedSection]) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []

    for section in sections:
        text = sanitize_text(section.text) or ""
        heading = sanitize_text(section.heading)

        if section.chunk_type != "text":
            drafts.append(
                ChunkDraft(
                    text=text,
                    chunk_type=section.chunk_type,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    heading=heading,
                    metadata=section.metadata,
                )
            )
            continue

        words = text.split()
        if not words:
            continue

        for window in _split_long_text(words):
            drafts.append(
                ChunkDraft(
                    text=" ".join(window),
                    chunk_type="text",
                    page_start=section.page_start,
                    page_end=section.page_end,
                    heading=heading,
                    metadata=section.metadata,
                )
            )

    return drafts

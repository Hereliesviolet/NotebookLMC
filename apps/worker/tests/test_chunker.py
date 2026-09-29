"""Chunking rules: sliding window for long text, tables kept whole."""

from app.chunking.chunker import MAX_WORDS, OVERLAP_WORDS, chunk_sections
from app.parsing.types import ParsedSection


def _words(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_short_text_section_is_one_chunk_with_metadata_preserved():
    section = ParsedSection(text="hello world", heading="Intro", page_start=2, page_end=3)

    chunks = chunk_sections([section])

    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].heading == "Intro"
    assert (chunks[0].page_start, chunks[0].page_end) == (2, 3)
    assert chunks[0].chunk_type == "text"


def test_empty_text_section_is_skipped():
    assert chunk_sections([ParsedSection(text="   \n\t ")]) == []


def test_long_text_is_split_into_overlapping_windows():
    total = MAX_WORDS + 300
    chunks = chunk_sections([ParsedSection(text=_words(total))])

    assert len(chunks) == 2
    first, second = (c.text.split() for c in chunks)
    assert len(first) == MAX_WORDS
    # The second window starts OVERLAP_WORDS before the end of the first one.
    assert second[0] == first[MAX_WORDS - OVERLAP_WORDS]
    assert second[-1] == f"w{total - 1}"


def test_text_at_exactly_max_words_is_not_split():
    chunks = chunk_sections([ParsedSection(text=_words(MAX_WORDS))])

    assert len(chunks) == 1


def test_table_section_is_kept_as_single_chunk_even_when_long():
    table = "| a | b |\n" + "\n".join(f"| {i} | {i} |" for i in range(MAX_WORDS))
    section = ParsedSection(text=table, chunk_type="table", metadata={"sheet": "S1"})

    chunks = chunk_sections([section])

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "table"
    assert chunks[0].metadata == {"sheet": "S1"}


def test_control_characters_are_stripped_before_chunking():
    chunks = chunk_sections([ParsedSection(text="a\x00b c", heading="h\x00")])

    assert chunks[0].text == "ab c"
    assert chunks[0].heading == "h"

from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    """One structural unit extracted from a document (a page, paragraph,
    heading section, table or slide) before chunking.
    """

    text: str
    heading: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_type: str = "text"  # text | table | image_caption | transcript | slide
    metadata: dict = field(default_factory=dict)

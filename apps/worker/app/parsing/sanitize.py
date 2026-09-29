"""Text sanitization shared by all parsers and the chunker.

Postgres rejects string literals containing NUL (0x00) bytes on insert, and
pypdf/python-docx/pandas+openpyxl can embed one in extracted text for certain
input files (custom font ToUnicode CMaps, corrupted cell content, etc.). Other
C0 control characters have no legitimate place in extracted document text
either, so they are stripped alongside NUL - except `\n`, `\r` and `\t`, which
are meaningful whitespace.
"""

import re

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str | None) -> str | None:
    if text is None:
        return None
    return _CONTROL_CHARS_RE.sub("", text)

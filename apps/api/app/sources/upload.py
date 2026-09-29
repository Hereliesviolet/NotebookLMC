"""File type validation for uploads.

Kept separate from service.py so the supported-type list is easy to find
and extend (PowerPoint/Audio/Video/OCR are explicitly out of scope for now).
"""

import mimetypes

SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class UnsupportedFileTypeError(ValueError):
    pass


def resolve_mime_type(filename: str, provided_content_type: str | None) -> str:
    """Trusts the file extension over the browser-provided content type,
    since browsers are inconsistent about content types for e.g. .md/.csv.
    """
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[suffix]

    guessed, _ = mimetypes.guess_type(filename)
    if guessed in SUPPORTED_MIME_TYPES:
        return guessed

    if provided_content_type in SUPPORTED_MIME_TYPES:
        return provided_content_type

    raise UnsupportedFileTypeError(
        f"Unsupported file type for '{filename}' (content_type={provided_content_type!r}). "
        f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )

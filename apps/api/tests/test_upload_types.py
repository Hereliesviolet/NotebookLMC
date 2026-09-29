"""Upload type resolution (extension wins over the browser content type)."""

import pytest

from app.sources.upload import UnsupportedFileTypeError, resolve_mime_type


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.pdf", "application/pdf"),
        ("notes.MD", "text/markdown"),
        ("notes.markdown", "text/markdown"),
        ("page.htm", "text/html"),
        ("data.csv", "text/csv"),
    ],
)
def test_supported_extensions_resolve_regardless_of_case(filename, expected):
    assert resolve_mime_type(filename, None) == expected


def test_extension_takes_precedence_over_provided_content_type():
    assert resolve_mime_type("notes.md", "application/octet-stream") == "text/markdown"


def test_supported_content_type_is_used_when_extension_is_unknown():
    assert resolve_mime_type("upload", "application/pdf") == "application/pdf"


def test_unsupported_type_is_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        resolve_mime_type("slides.pptx", "application/vnd.ms-powerpoint")

"""Vision-OCR fallback for scanned PDF pages without a text layer."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.parsing import pdf as pdf_module


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _fake_reader(*page_texts: str) -> MagicMock:
    pages = []
    for page_text in page_texts:
        page = MagicMock()
        page.extract_text.return_value = page_text
        pages.append(page)
    reader = MagicMock()
    reader.pages = pages
    return reader


def test_parse_pdf_skips_ocr_when_text_layer_present():
    reader = _fake_reader("A real text layer with plenty of characters on this page.")

    with patch.object(pdf_module, "PdfReader", return_value=reader), patch.object(
        pdf_module, "_ocr_page"
    ) as mock_ocr:
        sections = pdf_module.parse_pdf(b"irrelevant")

    mock_ocr.assert_not_called()
    assert len(sections) == 1
    assert "real text layer" in sections[0].text


def test_parse_pdf_falls_back_to_ocr_for_empty_text_layer():
    reader = _fake_reader("")

    with patch.object(pdf_module, "PdfReader", return_value=reader), patch.object(
        pdf_module, "_ocr_page", return_value="Text von Claude Vision erkannt"
    ) as mock_ocr:
        sections = pdf_module.parse_pdf(b"irrelevant")

    mock_ocr.assert_called_once()
    assert len(sections) == 1
    assert sections[0].text == "Text von Claude Vision erkannt"
    assert sections[0].page_start == 1


def test_parse_pdf_falls_back_to_ocr_for_near_empty_text_layer():
    reader = _fake_reader("\n \x00 ")  # below _MIN_TEXT_LAYER_CHARS after sanitize/strip

    with patch.object(pdf_module, "PdfReader", return_value=reader), patch.object(
        pdf_module, "_ocr_page", return_value="OCR-Ergebnis"
    ) as mock_ocr:
        sections = pdf_module.parse_pdf(b"irrelevant")

    mock_ocr.assert_called_once()
    assert sections[0].text == "OCR-Ergebnis"


def test_parse_pdf_respects_disabled_flag(monkeypatch):
    monkeypatch.setenv("PDF_OCR_FALLBACK_ENABLED", "false")
    get_settings.cache_clear()
    reader = _fake_reader("")

    with patch.object(pdf_module, "PdfReader", return_value=reader), patch.object(
        pdf_module, "_ocr_page"
    ) as mock_ocr:
        sections = pdf_module.parse_pdf(b"irrelevant")

    mock_ocr.assert_not_called()
    assert sections == []


def test_parse_pdf_returns_no_sections_when_ocr_also_finds_nothing():
    reader = _fake_reader("")

    with patch.object(pdf_module, "PdfReader", return_value=reader), patch.object(
        pdf_module, "_ocr_page", return_value=""
    ):
        sections = pdf_module.parse_pdf(b"irrelevant")

    assert sections == []

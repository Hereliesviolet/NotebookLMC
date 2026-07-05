"""PDF parsing (MVP choice: pypdf, see docs/architecture.md §14.4 recommendation).

Scanned/image-only PDFs have no embedded text layer, so pypdf.extract_text()
returns nothing for them. Pages below `_MIN_TEXT_LAYER_CHARS` are rendered to
JPEG via `pdftoppm` (poppler-utils) and sent through Claude Vision (Langdock
client) as an OCR fallback - see docs/architecture.md §14.2. Pages with a
usable text layer are left untouched (no extra Vision call/cost).
"""
import glob
import io
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

from app.core.config import get_settings
from app.core.logging import get_logger
from app.langdock.client import get_langdock_client
from app.parsing.sanitize import sanitize_text
from app.parsing.types import ParsedSection

logger = get_logger(__name__)

_MIN_TEXT_LAYER_CHARS = 20
_RENDER_DPI = 150
_PDFTOPPM_TIMEOUT_SECONDS = 60


def _render_page_to_jpeg(pdf_path: str, page_number: int, out_dir: str) -> bytes | None:
    prefix = f"{out_dir}/page"
    try:
        subprocess.run(
            [
                "pdftoppm",
                "-jpeg",
                "-r",
                str(_RENDER_DPI),
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-jpegopt",
                "quality=85",
                pdf_path,
                prefix,
            ],
            check=True,
            capture_output=True,
            timeout=_PDFTOPPM_TIMEOUT_SECONDS,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.error("pdftoppm failed to render page %d: %s", page_number, exc)
        return None

    matches = sorted(glob.glob(f"{prefix}-*.jpg"))
    if not matches:
        logger.error("pdftoppm produced no output file for page %d", page_number)
        return None
    return Path(matches[0]).read_bytes()


def _ocr_page(pdf_path: str, page_number: int, out_dir: str) -> str:
    image_bytes = _render_page_to_jpeg(pdf_path, page_number, out_dir)
    if image_bytes is None:
        return ""

    client = get_langdock_client()
    try:
        response = client.extract_text_from_image(image_bytes)
    except Exception:
        logger.exception("Vision OCR failed for page %d", page_number)
        return ""

    logger.info(
        "Vision OCR for page %d done (model=%s, latency_ms=%s, output_tokens=%s)",
        page_number,
        response.usage.model,
        response.usage.latency_ms,
        response.usage.output_tokens,
    )
    return sanitize_text(response.text or "").strip()


def parse_pdf(data: bytes) -> list[ParsedSection]:
    settings = get_settings()
    reader = PdfReader(io.BytesIO(data))
    sections: list[ParsedSection] = []

    tmp_dir: tempfile.TemporaryDirectory | None = None
    pdf_path: str | None = None

    try:
        for page_index, page in enumerate(reader.pages, start=1):
            text = sanitize_text(page.extract_text() or "").strip()

            if len(text) < _MIN_TEXT_LAYER_CHARS and settings.pdf_ocr_fallback_enabled:
                logger.info(
                    "page %d has no usable text layer (%d chars) - falling back to Vision OCR",
                    page_index,
                    len(text),
                )
                if tmp_dir is None:
                    tmp_dir = tempfile.TemporaryDirectory()
                    pdf_path = f"{tmp_dir.name}/source.pdf"
                    Path(pdf_path).write_bytes(data)
                text = _ocr_page(pdf_path, page_index, tmp_dir.name)

            if not text:
                continue
            sections.append(ParsedSection(text=text, page_start=page_index, page_end=page_index, chunk_type="text"))
    finally:
        if tmp_dir is not None:
            tmp_dir.cleanup()

    return sections

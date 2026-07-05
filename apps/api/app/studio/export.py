"""Server-side Word (.docx) / PDF export for Studio artifacts (architecture
doc §19). Renders a persisted artifact's `content_json` (shape depends on
`type`, see packages/prompts/studio_*_tool_schema.json) into a docx.Document
and into an HTML string (rendered to PDF via WeasyPrint). Both renderers
share the same tiny markdown parser and the same per-type block builders so
the two output formats stay visually consistent.
"""
import html
import re
from datetime import datetime
from io import BytesIO

from docx import Document
from docx.shared import Pt
from jinja2 import BaseLoader, Environment
from weasyprint import HTML as WeasyHTML

ARTIFACT_TITLES = {
    "summary": "Zusammenfassung",
    "faq": "Häufig gestellte Fragen (FAQ)",
    "timeline": "Timeline",
    "briefing": "Briefing",
}

_BRIEFING_SECTIONS = [
    ("key_points", "Kernpunkte"),
    ("risks", "Risiken"),
    ("recommended_actions", "Handlungsempfehlungen"),
    ("open_questions", "Offene Fragen"),
]

# --- tiny markdown parsing shared between the docx and HTML renderers ---
# Just enough for Sonnet's typical summary_markdown output (ATX headings,
# **bold**/*italic*/`code`, bullet/numbered lists, fenced code, tables kept
# as preformatted blocks) - not a full CommonMark implementation.

_INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|`.+?`|\*.+?\*)")


def _parse_inline(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    for part in _INLINE_PATTERN.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            tokens.append((part[2:-2], "bold"))
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            tokens.append((part[1:-1], "code"))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            tokens.append((part[1:-1], "italic"))
        else:
            tokens.append((part, "plain"))
    return tokens


def _parse_markdown_blocks(markdown_text: str) -> list[dict]:
    blocks: list[dict] = []
    lines = markdown_text.splitlines()
    list_buffer: list[str] = []
    list_type: str | None = None

    def flush_list() -> None:
        nonlocal list_buffer, list_type
        if list_buffer:
            blocks.append({"type": list_type, "items": list_buffer})
        list_buffer = []
        list_type = None

    in_code = False
    code_lines: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith("```"):
            if in_code:
                blocks.append({"type": "code", "text": "\n".join(code_lines)})
                code_lines = []
                in_code = False
            else:
                flush_list()
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(lines[i])
            i += 1
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading_match:
            flush_list()
            blocks.append({"type": "heading", "level": len(heading_match.group(1)), "text": heading_match.group(2).strip()})
            i += 1
            continue

        if stripped in ("", "---", "***"):
            flush_list()
            i += 1
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            if list_type != "bullet_list":
                flush_list()
                list_type = "bullet_list"
            list_buffer.append(bullet_match.group(1))
            i += 1
            continue

        numbered_match = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if numbered_match:
            if list_type != "numbered_list":
                flush_list()
                list_type = "numbered_list"
            list_buffer.append(numbered_match.group(1))
            i += 1
            continue

        if stripped.startswith("|"):
            flush_list()
            table_lines = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            blocks.append({"type": "code", "text": "\n".join(table_lines)})
            continue

        flush_list()
        blocks.append({"type": "paragraph", "text": stripped})
        i += 1

    flush_list()
    if in_code and code_lines:
        blocks.append({"type": "code", "text": "\n".join(code_lines)})
    return blocks


# --- docx rendering ---


def _add_inline_runs(paragraph, text: str) -> None:
    for token_text, style in _parse_inline(text):
        run = paragraph.add_run(token_text)
        if style == "bold":
            run.bold = True
        elif style == "italic":
            run.italic = True
        elif style == "code":
            run.font.name = "Courier New"


def _add_meta_paragraph(document, text: str) -> None:
    paragraph = document.add_paragraph()
    run = paragraph.add_run(text)
    run.italic = True
    run.font.size = Pt(9)


def _markdown_blocks_to_docx(document, blocks: list[dict]) -> None:
    for block in blocks:
        if block["type"] == "heading":
            document.add_heading(block["text"], level=block["level"])
        elif block["type"] in ("bullet_list", "numbered_list"):
            style = "List Bullet" if block["type"] == "bullet_list" else "List Number"
            for item in block["items"]:
                _add_inline_runs(document.add_paragraph(style=style), item)
        elif block["type"] == "code":
            run = document.add_paragraph().add_run(block["text"])
            run.font.name = "Courier New"
            run.font.size = Pt(9)
        else:
            _add_inline_runs(document.add_paragraph(), block["text"])


def _faq_to_docx(document, content: dict) -> None:
    for item in content.get("items") or []:
        document.add_heading(item.get("question", ""), level=2)
        _add_inline_runs(document.add_paragraph(), item.get("answer", ""))
        source_ids = item.get("source_ids") or []
        if source_ids:
            _add_meta_paragraph(document, "Quellen: " + ", ".join(source_ids))


def _sorted_timeline_events(content: dict) -> list[dict]:
    events = content.get("events") or []
    dated = [e for e in events if e.get("date")]
    undated = [e for e in events if not e.get("date")]
    dated.sort(key=lambda e: e["date"])
    return dated + undated


def _timeline_to_docx(document, content: dict) -> None:
    for event in _sorted_timeline_events(content):
        document.add_heading(event.get("date_label") or event.get("date") or "Unklar", level=2)
        _add_inline_runs(document.add_paragraph(), event.get("description", ""))
        quote = event.get("quote")
        if quote:
            run = document.add_paragraph().add_run(f"„{quote}“")
            run.italic = True
        _add_meta_paragraph(document, f"Quelle: {event.get('source_id', '')}")


def _briefing_to_docx(document, content: dict) -> None:
    document.add_heading("Zusammenfassung", level=2)
    _add_inline_runs(document.add_paragraph(), content.get("summary", ""))
    for field, title in _BRIEFING_SECTIONS:
        items = content.get(field) or []
        document.add_heading(title, level=2)
        if not items:
            document.add_paragraph("– keine –")
            continue
        for item in items:
            _add_inline_runs(document.add_paragraph(style="List Bullet"), item)


def build_docx(artifact_type: str, notebook_title: str, content: dict, generated_at: datetime) -> Document:
    document = Document()
    document.add_heading(f"{ARTIFACT_TITLES[artifact_type]}: {notebook_title}", level=0)
    _add_meta_paragraph(document, f"Generiert am {generated_at.strftime('%d.%m.%Y %H:%M')} Uhr")

    if artifact_type == "summary":
        _markdown_blocks_to_docx(document, _parse_markdown_blocks(content.get("summary_markdown", "")))
    elif artifact_type == "faq":
        _faq_to_docx(document, content)
    elif artifact_type == "timeline":
        _timeline_to_docx(document, content)
    elif artifact_type == "briefing":
        _briefing_to_docx(document, content)
    else:
        raise ValueError(f"Unknown studio artifact type: {artifact_type!r}")
    return document


def render_docx_bytes(document: Document) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


# --- HTML / PDF rendering ---


def _inline_to_html(text: str) -> str:
    parts = []
    for token_text, style in _parse_inline(text):
        escaped = html.escape(token_text)
        if style == "bold":
            parts.append(f"<strong>{escaped}</strong>")
        elif style == "italic":
            parts.append(f"<em>{escaped}</em>")
        elif style == "code":
            parts.append(f"<code>{escaped}</code>")
        else:
            parts.append(escaped)
    return "".join(parts)


def _markdown_blocks_to_html(blocks: list[dict]) -> str:
    parts = []
    for block in blocks:
        if block["type"] == "heading":
            level = block["level"] + 1  # +1: document <h1> is the artifact title
            parts.append(f"<h{level}>{_inline_to_html(block['text'])}</h{level}>")
        elif block["type"] in ("bullet_list", "numbered_list"):
            tag = "ul" if block["type"] == "bullet_list" else "ol"
            items = "".join(f"<li>{_inline_to_html(i)}</li>" for i in block["items"])
            parts.append(f"<{tag}>{items}</{tag}>")
        elif block["type"] == "code":
            parts.append(f"<pre>{html.escape(block['text'])}</pre>")
        else:
            parts.append(f"<p>{_inline_to_html(block['text'])}</p>")
    return "\n".join(parts)


def _faq_to_html(content: dict) -> str:
    parts = []
    for item in content.get("items") or []:
        parts.append(f"<h2>{_inline_to_html(item.get('question', ''))}</h2>")
        parts.append(f"<p>{_inline_to_html(item.get('answer', ''))}</p>")
        source_ids = item.get("source_ids") or []
        if source_ids:
            parts.append(f"<p class='meta'>Quellen: {html.escape(', '.join(source_ids))}</p>")
    return "\n".join(parts)


def _timeline_to_html(content: dict) -> str:
    parts = []
    for event in _sorted_timeline_events(content):
        label = event.get("date_label") or event.get("date") or "Unklar"
        parts.append(f"<h2>{html.escape(str(label))}</h2>")
        parts.append(f"<p>{_inline_to_html(event.get('description', ''))}</p>")
        quote = event.get("quote")
        if quote:
            parts.append(f"<blockquote>{_inline_to_html(quote)}</blockquote>")
        parts.append(f"<p class='meta'>Quelle: {html.escape(str(event.get('source_id', '')))}</p>")
    return "\n".join(parts)


def _briefing_to_html(content: dict) -> str:
    parts = [f"<h2>Zusammenfassung</h2><p>{_inline_to_html(content.get('summary', ''))}</p>"]
    for field, title in _BRIEFING_SECTIONS:
        items = content.get(field) or []
        parts.append(f"<h2>{title}</h2>")
        if not items:
            parts.append("<p>– keine –</p>")
        else:
            lis = "".join(f"<li>{_inline_to_html(i)}</li>" for i in items)
            parts.append(f"<ul>{lis}</ul>")
    return "\n".join(parts)


_HTML_TEMPLATE = Environment(loader=BaseLoader(), autoescape=True).from_string(
    """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
  body { font-family: 'Liberation Sans', Arial, sans-serif; color: #1a1a1a; font-size: 11pt; line-height: 1.5; }
  h1 { font-size: 20pt; margin-bottom: 4pt; }
  .subtitle { color: #666; font-size: 10pt; margin-top: 0; margin-bottom: 20pt; }
  h2 { font-size: 14pt; margin-top: 18pt; border-bottom: 1px solid #ddd; padding-bottom: 2pt; }
  h3, h4 { font-size: 12pt; margin-top: 12pt; }
  p { margin: 6pt 0; }
  ul, ol { margin: 6pt 0; padding-left: 20pt; }
  blockquote { border-left: 3px solid #999; margin: 8pt 0; padding: 2pt 10pt; color: #444; font-style: italic; }
  code, pre { font-family: 'Courier New', monospace; font-size: 9.5pt; }
  pre { background: #f4f4f4; padding: 8pt; white-space: pre-wrap; }
  .meta { color: #777; font-size: 9pt; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<p class="subtitle">{{ subtitle }}</p>
{{ body | safe }}
</body>
</html>"""
)


def build_html(artifact_type: str, notebook_title: str, content: dict, generated_at: datetime) -> str:
    if artifact_type == "summary":
        body = _markdown_blocks_to_html(_parse_markdown_blocks(content.get("summary_markdown", "")))
    elif artifact_type == "faq":
        body = _faq_to_html(content)
    elif artifact_type == "timeline":
        body = _timeline_to_html(content)
    elif artifact_type == "briefing":
        body = _briefing_to_html(content)
    else:
        raise ValueError(f"Unknown studio artifact type: {artifact_type!r}")

    return _HTML_TEMPLATE.render(
        title=f"{ARTIFACT_TITLES[artifact_type]}: {notebook_title}",
        subtitle=f"Generiert am {generated_at.strftime('%d.%m.%Y %H:%M')} Uhr",
        body=body,
    )


def render_pdf_bytes(html_content: str) -> bytes:
    return WeasyHTML(string=html_content).write_pdf()


def safe_filename(base: str, extension: str) -> str:
    ascii_base = base.encode("ascii", "ignore").decode("ascii")
    ascii_base = re.sub(r"[^A-Za-z0-9._ -]", "_", ascii_base).strip(" ._") or "export"
    return f"{ascii_base}.{extension}"

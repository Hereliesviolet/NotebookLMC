"""Infographic rasterize pipeline (architecture doc §19): renders a Studio
`infographic` artifact's content_json into a fixed-size poster PNG. Reuses
apps/api/app/studio/export.py's design tokens so the poster matches the
rest of the Studio exports, then goes HTML -> PDF (WeasyPrint) -> PNG
(pdf2image/poppler) since WeasyPrint itself only produces PDF/(non-raster)
output.
"""
from io import BytesIO

from jinja2 import BaseLoader, Environment
from pdf2image import convert_from_bytes
from weasyprint import HTML as WeasyHTML

from app.studio.export import AMBER, BORDER, FOREGROUND, GREEN, MUTED, PRIMARY, RED, _tint

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 1600
_DPI = 96  # 96 CSS px/inch == 1 CSS px per rasterized pixel at this dpi

_BADGE_COLORS = [PRIMARY, GREEN, AMBER, RED]

_TEMPLATE = Environment(loader=BaseLoader(), autoescape=True).from_string(
    """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<style>
  @page { size: {{ width }}px {{ height }}px; margin: 0; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: {{ height }}px; }
  body { display: flex; flex-direction: column; font-family: 'Liberation Sans', Arial, sans-serif; color: {{ foreground }}; width: {{ width }}px; }
  .header { flex: none; background: {{ primary }}; color: #fff; padding: 64px 64px 52px 64px; }
  .headline { font-size: 44px; font-weight: 700; margin: 0 0 18px 0; line-height: 1.25; }
  .subheadline { font-size: 22px; font-weight: 400; opacity: 0.9; margin: 0; }
  .content { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 48px; padding: 56px 64px; }
  .stats { display: flex; gap: 28px; }
  .stat { flex: 1; background: {{ primary_tint }}; border-radius: 16px; padding: 30px 16px; text-align: center; }
  .stat-value { font-size: 28px; font-weight: 700; color: {{ primary }}; line-height: 1.25; }
  .stat-label { font-size: 15px; color: {{ muted }}; margin-top: 10px; }
  .sections { display: grid; grid-template-columns: repeat({{ columns }}, 1fr); gap: 28px; }
  .section-card { border: 1px solid {{ border }}; border-radius: 16px; padding: 34px 30px; background: #fff; }
  .badge { width: 48px; height: 48px; border-radius: 50%; color: #fff; font-size: 22px; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; }
  .section-title { font-size: 24px; font-weight: 700; margin: 0 0 14px 0; }
  .section-body { font-size: 18px; line-height: 1.55; color: {{ foreground }}; margin: 0; }
  .footer { flex: none; text-align: center; font-size: 14px; color: {{ muted }}; padding: 0 0 40px 0; }
</style>
</head>
<body>
  <div class="header">
    <p class="headline">{{ headline }}</p>
    <p class="subheadline">{{ subheadline }}</p>
  </div>
  <div class="content">
    {% if stats %}
    <div class="stats">
      {% for stat in stats %}
      <div class="stat">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
    <div class="sections">
      {% for section in sections %}
      <div class="section-card">
        <div class="badge" style="background: {{ badge_colors[loop.index0 % badge_colors|length] }};">{{ loop.index }}</div>
        <p class="section-title">{{ section.title }}</p>
        <p class="section-body">{{ section.body }}</p>
      </div>
      {% endfor %}
    </div>
  </div>
  <div class="footer">Erstellt mit NotebookLM Clone</div>
</body>
</html>"""
)


def build_html(content: dict) -> str:
    sections = (content.get("sections") or [])[:4]
    stats = (content.get("stats") or [])[:4]
    return _TEMPLATE.render(
        width=CANVAS_WIDTH,
        height=CANVAS_HEIGHT,
        columns=3 if len(sections) == 3 else 2,
        primary=PRIMARY,
        primary_tint=_tint(PRIMARY),
        muted=MUTED,
        border=BORDER,
        foreground=FOREGROUND,
        headline=content.get("headline", ""),
        subheadline=content.get("subheadline", ""),
        sections=sections,
        stats=stats,
        badge_colors=_BADGE_COLORS,
    )


def render_png(content: dict) -> bytes:
    pdf_bytes = WeasyHTML(string=build_html(content)).write_pdf()
    images = convert_from_bytes(pdf_bytes, dpi=_DPI, fmt="png")
    buffer = BytesIO()
    images[0].save(buffer, format="PNG")
    return buffer.getvalue()

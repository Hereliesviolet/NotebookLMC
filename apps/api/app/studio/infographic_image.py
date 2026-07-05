"""Deterministic image-generation prompt for the Studio infographic
(architecture doc §19). Builds a plain Python template string from the
structured content Sonnet already produced (studio_infographic_tool_schema.json)
- no extra LLM text round-trip for the image prompt itself.

Replaces the former WeasyPrint/pdf2image rasterize pipeline
(apps/api/app/studio/infographic_render.py) as the actual image *source*:
the resulting prompt is sent to a Langdock agent with the "Image Generation"
capability enabled (LangdockClient.generate_agent_image()).
"""

# export.py's PRIMARY (#463ACB / hsl(245 58% 51%)) described as a color name
# rather than a CSS value, since image models respond far more reliably to
# names than to hsl()/hex values - verified against the real agent: "purple
# header band" reliably produced a matching dark indigo tone.
_ACCENT_COLOR_NAME = "purple"

_MAX_CARDS = 4


def build_infographic_image_prompt(content: dict) -> str:
    headline = (content.get("headline") or "").replace('"', "'")
    sections = (content.get("sections") or [])[:_MAX_CARDS]
    card_list = ", ".join(
        f"{index}) {(section.get('title') or '').replace(chr(34), chr(39))}"
        for index, section in enumerate(sections, start=1)
    )

    return (
        "Generate a clean, modern business infographic poster, portrait format, white "
        f'background, {_ACCENT_COLOR_NAME} header band with the exact headline text "{headline}" '
        "in bold white letters. Below the header, "
        f"{len(sections)} rounded rectangle cards in a grid, each with a numbered circle badge "
        f"and a short title: {card_list}. Minimal flat design, no photos, no people. Use the "
        "image generation tool to create this as a single image."
    )

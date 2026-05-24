"""
Custom Word styles for the BPD template.

We register reusable named styles on the document so formatting stays
consistent and lives in one place. Headings inherit from the built-in
Heading 1 / Heading 2 styles so the auto-generated Table of Contents
picks them up via their outline level.
"""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor


# Style name constants — referenced from the builder so we never type
# the raw string in more than one place.
HEADING_STYLE = "BPD Heading"
SUBHEADING_STYLE = "BPD Subheading"
NORMAL_HEADING_STYLE = "BPD Normal Heading"
BODY_STYLE = "BPD Body"
TABLE_STYLE = "BPD Table"

FONT_NAME = "Calibri"
BLACK = RGBColor(0x00, 0x00, 0x00)


def _set_font(style, *, size_pt: int, bold: bool) -> None:
    font = style.font
    font.name = FONT_NAME
    font.size = Pt(size_pt)
    font.bold = bold
    font.color.rgb = BLACK


def register_styles(doc: DocxDocument) -> None:
    """Idempotently register all BPD styles on the document."""
    styles = doc.styles

    # --- Heading (level 1) ----------------------------------------------------
    if HEADING_STYLE not in [s.name for s in styles]:
        heading = styles.add_style(HEADING_STYLE, WD_STYLE_TYPE.PARAGRAPH)
        # Inherit outline level 0 from Heading 1 so TOC picks it up.
        heading.base_style = styles["Heading 1"]
        _set_font(heading, size_pt=16, bold=True)
        heading.paragraph_format.space_before = Pt(8)
        heading.paragraph_format.space_after = Pt(8)
        heading.paragraph_format.keep_with_next = True

    # --- Subheading (level 2) -------------------------------------------------
    if SUBHEADING_STYLE not in [s.name for s in styles]:
        sub = styles.add_style(SUBHEADING_STYLE, WD_STYLE_TYPE.PARAGRAPH)
        sub.base_style = styles["Heading 2"]
        _set_font(sub, size_pt=14, bold=True)
        sub.paragraph_format.space_before = Pt(6)
        sub.paragraph_format.space_after = Pt(4)
        sub.paragraph_format.keep_with_next = True

    # --- Normal Heading (NOT in TOC) -----------------------------------------
    if NORMAL_HEADING_STYLE not in [s.name for s in styles]:
        nh = styles.add_style(NORMAL_HEADING_STYLE, WD_STYLE_TYPE.PARAGRAPH)
        nh.base_style = styles["Normal"]
        _set_font(nh, size_pt=12, bold=True)
        # Per spec: no empty line after this heading.
        nh.paragraph_format.space_before = Pt(2)
        nh.paragraph_format.space_after = Pt(0)
        nh.paragraph_format.keep_with_next = True

    # --- Body paragraph -------------------------------------------------------
    if BODY_STYLE not in [s.name for s in styles]:
        body = styles.add_style(BODY_STYLE, WD_STYLE_TYPE.PARAGRAPH)
        body.base_style = styles["Normal"]
        _set_font(body, size_pt=11, bold=False)
        body.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        body.paragraph_format.space_after = Pt(0)
        body.paragraph_format.space_before = Pt(0)
        body.paragraph_format.line_spacing = 1.0

    # --- Table cell text style ------------------------------------------------
    if TABLE_STYLE not in [s.name for s in styles]:
        tbl = styles.add_style(TABLE_STYLE, WD_STYLE_TYPE.PARAGRAPH)
        tbl.base_style = styles["Normal"]
        _set_font(tbl, size_pt=10, bold=False)
        tbl.paragraph_format.space_before = Pt(0)
        tbl.paragraph_format.space_after = Pt(0)

    # Override the document default font so anything we forget still
    # renders in Calibri.
    normal = styles["Normal"]
    normal.font.name = FONT_NAME
    normal.font.size = Pt(11)

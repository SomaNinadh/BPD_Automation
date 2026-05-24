"""
Block data models for the BPD document builder.

Each block represents one renderable unit in the final Word document.
Blocks are intentionally dumb data containers — all rendering logic
lives in the builder, so new block types can be added without changing
the UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class BlockType(str, Enum):
    HEADING = "Heading"
    SUBHEADING = "Subheading"
    NORMAL_HEADING = "Normal Heading"
    PARAGRAPH = "Paragraph"
    IMAGE = "Image"
    TABLE = "Table"


@dataclass
class Block:
    """Base class so the builder can dispatch on isinstance."""
    block_type: BlockType


@dataclass
class HeadingBlock(Block):
    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__(BlockType.HEADING)
        self.text = text


@dataclass
class SubheadingBlock(Block):
    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__(BlockType.SUBHEADING)
        self.text = text


@dataclass
class NormalHeadingBlock(Block):
    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__(BlockType.NORMAL_HEADING)
        self.text = text


@dataclass
class ParagraphBlock(Block):
    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__(BlockType.PARAGRAPH)
        self.text = text


@dataclass
class ImageBlock(Block):
    # Raw image bytes so the block is self-contained (works with uploads
    # that don't have a real filesystem path).
    image_bytes: Optional[bytes] = None
    filename: str = ""
    # Fraction of the page content width (0.0 - 1.0). Default keeps images
    # uniform across the document.
    width_ratio: float = 0.7

    def __init__(self, image_bytes: Optional[bytes] = None, filename: str = "", width_ratio: float = 0.7):
        super().__init__(BlockType.IMAGE)
        self.image_bytes = image_bytes
        self.filename = filename
        self.width_ratio = width_ratio


@dataclass
class TableBlock(Block):
    rows: int = 2
    cols: int = 2
    # data[row][col]; row 0 is the header.
    data: List[List[str]] = field(default_factory=list)

    def __init__(self, rows: int = 2, cols: int = 2, data: Optional[List[List[str]]] = None):
        super().__init__(BlockType.TABLE)
        self.rows = rows
        self.cols = cols
        if data is None:
            data = [["" for _ in range(cols)] for _ in range(rows)]
        self.data = data

    def ensure_shape(self) -> None:
        """Resize the data matrix to match rows/cols, preserving existing cells."""
        new_data: List[List[str]] = []
        for r in range(self.rows):
            row: List[str] = []
            for c in range(self.cols):
                if r < len(self.data) and c < len(self.data[r]):
                    row.append(self.data[r][c])
                else:
                    row.append("")
            new_data.append(row)
        self.data = new_data

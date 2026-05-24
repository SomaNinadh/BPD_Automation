"""
Streamlit widgets for editing each block type.

The render function picks the right editor based on block type and
writes user input straight back into the session-state payload.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from src.document.blocks import BlockType
from src.ui import state


def _editor_key(block_id: str, suffix: str) -> str:
    return f"block-{block_id}-{suffix}"


def get_block_label(index: int, block: Dict[str, Any]) -> str:
    """Build a short label for reorder UIs and expander headers."""
    block_type: BlockType = block["type"]
    label_preview = ""
    payload = block["payload"]
    if block_type in (
        BlockType.HEADING,
        BlockType.SUBHEADING,
        BlockType.NORMAL_HEADING,
        BlockType.PARAGRAPH,
    ):
        preview = (payload.get("text") or "").strip().splitlines()[0:1]
        label_preview = preview[0][:40] if preview else ""

    header = f"#{index + 1} - {block_type.value}"
    if label_preview:
        header += f" - {label_preview}"
    return header


def _render_text_editor(block: Dict[str, Any], *, label: str, multiline: bool) -> None:
    key = _editor_key(block["id"], "text")
    if multiline:
        block["payload"]["text"] = st.text_area(
            label,
            value=block["payload"].get("text", ""),
            key=key,
            height=140,
        )
    else:
        block["payload"]["text"] = st.text_input(
            label,
            value=block["payload"].get("text", ""),
            key=key,
        )


def _render_image_editor(block: Dict[str, Any]) -> None:
    upload_key = _editor_key(block["id"], "upload")
    width_key = _editor_key(block["id"], "width")

    uploaded = st.file_uploader(
        "Upload image (PNG / JPG)",
        type=["png", "jpg", "jpeg"],
        key=upload_key,
    )
    if uploaded is not None:
        block["payload"]["image_bytes"] = uploaded.getvalue()
        block["payload"]["filename"] = uploaded.name

    if block["payload"].get("image_bytes"):
        st.image(block["payload"]["image_bytes"], caption=block["payload"].get("filename"), width=240)

    block["payload"]["width_ratio"] = st.slider(
        "Width (fraction of page content)",
        min_value=0.2,
        max_value=1.0,
        value=float(block["payload"].get("width_ratio", 0.7)),
        step=0.05,
        key=width_key,
    )


def _render_table_editor(block: Dict[str, Any]) -> None:
    rows_key = _editor_key(block["id"], "rows")
    cols_key = _editor_key(block["id"], "cols")
    paste_key = _editor_key(block["id"], "paste")
    paste_button_key = _editor_key(block["id"], "paste-apply")
    payload = block["payload"]

    st.caption("Paste a table from Excel or Word, then apply it to fill the grid automatically.")
    pasted_text = st.text_area(
        "Paste table data",
        key=paste_key,
        height=120,
        placeholder="Copy cells from Excel or a table from Word and paste here...",
    )
    if st.button("Apply pasted table", key=paste_button_key, use_container_width=True):
        state.import_table_text(block["id"], pasted_text)
        payload = block["payload"]
        st.session_state[rows_key] = int(payload.get("rows", 1))
        st.session_state[cols_key] = int(payload.get("cols", 1))
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        rows = st.number_input(
            "Rows (incl. header)",
            min_value=1,
            max_value=50,
            value=int(payload.get("rows", 2)),
            step=1,
            key=rows_key,
        )
    with c2:
        cols = st.number_input(
            "Columns",
            min_value=1,
            max_value=12,
            value=int(payload.get("cols", 2)),
            step=1,
            key=cols_key,
        )

    if rows != payload.get("rows") or cols != payload.get("cols"):
        state.resize_table(block["id"], rows, cols)
        payload = block["payload"]

    st.caption("Row 1 is the header (bold, grey background).")
    for r in range(payload["rows"]):
        cols_widgets = st.columns(payload["cols"])
        for c, col_widget in enumerate(cols_widgets):
            cell_key = _editor_key(block["id"], f"cell-{r}-{c}")
            with col_widget:
                payload["data"][r][c] = st.text_input(
                    label=f"R{r + 1}C{c + 1}",
                    value=payload["data"][r][c],
                    key=cell_key,
                    label_visibility="collapsed",
                    placeholder=f"R{r + 1}C{c + 1}",
                )


def render_block_card(index: int, block: Dict[str, Any], total: int) -> None:
    """Render one block's editor inside an expander with reorder controls."""
    block_type: BlockType = block["type"]
    header = get_block_label(index, block)

    with st.expander(header, expanded=True):
        if block_type == BlockType.HEADING:
            _render_text_editor(block, label="Heading text (auto-uppercased & numbered)", multiline=False)
        elif block_type == BlockType.SUBHEADING:
            _render_text_editor(block, label="Subheading text (auto-uppercased & numbered)", multiline=False)
        elif block_type == BlockType.NORMAL_HEADING:
            _render_text_editor(block, label="Normal heading text (not in TOC)", multiline=False)
        elif block_type == BlockType.PARAGRAPH:
            _render_text_editor(block, label="Body paragraph", multiline=True)
        elif block_type == BlockType.IMAGE:
            _render_image_editor(block)
        elif block_type == BlockType.TABLE:
            _render_table_editor(block)

        b1, b2, b3, _ = st.columns([1, 1, 1, 6])
        with b1:
            st.button(
                "↑",
                key=_editor_key(block["id"], "up"),
                disabled=index == 0,
                on_click=state.move_block,
                args=(block["id"], -1),
                help="Move up",
            )
        with b2:
            st.button(
                "↓",
                key=_editor_key(block["id"], "down"),
                disabled=index == total - 1,
                on_click=state.move_block,
                args=(block["id"], 1),
                help="Move down",
            )
        with b3:
            st.button(
                "Delete",
                key=_editor_key(block["id"], "del"),
                on_click=state.remove_block,
                args=(block["id"],),
            )

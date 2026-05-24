"""
Session-state helpers for the Streamlit UI.

Keeps mutation of ``st.session_state`` in one place so the page module
can stay focused on rendering.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections import Counter
from copy import deepcopy
from typing import Any, Dict, List

import streamlit as st

from src.document import DocumentBranding
from src.document.blocks import (
    BlockType,
    HeadingBlock,
    ImageBlock,
    NormalHeadingBlock,
    ParagraphBlock,
    SubheadingBlock,
    TableBlock,
)


BLOCKS_KEY = "bpd_blocks"
DOC_META_KEY = "bpd_document_meta"
AUTH_KEY = "bpd_auth"
CURRENT_DRAFT_ID_KEY = "bpd_current_draft_id"
CURRENT_DRAFT_NAME_KEY = "bpd_current_draft_name"
LAST_SAVED_SNAPSHOT_KEY = "bpd_last_saved_snapshot"
SCHEMA_VERSION = 1


def _new_payload(block_type: BlockType) -> Dict[str, Any]:
    """Default editable payload for each block type."""
    if block_type in (
        BlockType.HEADING,
        BlockType.SUBHEADING,
        BlockType.NORMAL_HEADING,
        BlockType.PARAGRAPH,
    ):
        return {"text": ""}
    if block_type == BlockType.IMAGE:
        return {"image_bytes": None, "filename": "", "width_ratio": 0.7}
    if block_type == BlockType.TABLE:
        rows, cols = 2, 2
        return {
            "rows": rows,
            "cols": cols,
            "data": [["" for _ in range(cols)] for _ in range(rows)],
        }
    raise ValueError(f"Unknown block type: {block_type}")


def _default_document_meta() -> Dict[str, Any]:
    return {
        "header_title": "",
        "module_name": "",
        "project_name": "S4 HANA SANMAR",
    }


def _default_project_state_snapshot() -> Dict[str, Any]:
    document_meta = _default_document_meta()
    document_meta["client_logo_base64"] = _encode_bytes(document_meta.pop("client_logo_bytes", None))
    return {
        "schema_version": SCHEMA_VERSION,
        "document_meta": document_meta,
        "blocks": [],
    }


def _reset_widget_state() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("block-"):
            del st.session_state[key]
    for key in (
        "doc_header_title",
        "doc_module_name",
        "doc_project_name",
        "draft_name_input",
    ):
        if key in st.session_state:
            del st.session_state[key]


def _encode_bytes(value: bytes | None) -> str | None:
    if value is None:
        return None
    return base64.b64encode(value).decode("utf-8")


def _decode_bytes(value: str | None) -> bytes | None:
    if not value:
        return None
    return base64.b64decode(value.encode("utf-8"))


def init_state() -> None:
    if BLOCKS_KEY not in st.session_state:
        st.session_state[BLOCKS_KEY] = []  # list of {id, type, payload}
    if DOC_META_KEY not in st.session_state:
        st.session_state[DOC_META_KEY] = _default_document_meta()
    if AUTH_KEY not in st.session_state:
        st.session_state[AUTH_KEY] = {}
    if CURRENT_DRAFT_ID_KEY not in st.session_state:
        st.session_state[CURRENT_DRAFT_ID_KEY] = None
    if CURRENT_DRAFT_NAME_KEY not in st.session_state:
        st.session_state[CURRENT_DRAFT_NAME_KEY] = ""
    if LAST_SAVED_SNAPSHOT_KEY not in st.session_state:
        st.session_state[LAST_SAVED_SNAPSHOT_KEY] = None


def get_blocks() -> List[Dict[str, Any]]:
    return st.session_state[BLOCKS_KEY]


def get_document_meta() -> Dict[str, Any]:
    return st.session_state[DOC_META_KEY]


def get_auth_state() -> Dict[str, Any]:
    return st.session_state[AUTH_KEY]


def set_auth_state(auth_state: Dict[str, Any]) -> None:
    st.session_state[AUTH_KEY] = auth_state


def clear_auth_state() -> None:
    st.session_state[AUTH_KEY] = {}


def get_current_draft_id() -> str | None:
    return st.session_state[CURRENT_DRAFT_ID_KEY]


def get_current_draft_name() -> str:
    return st.session_state[CURRENT_DRAFT_NAME_KEY]


def set_current_draft(draft_id: str | None, draft_name: str) -> None:
    st.session_state[CURRENT_DRAFT_ID_KEY] = draft_id
    st.session_state[CURRENT_DRAFT_NAME_KEY] = draft_name


def clear_current_draft() -> None:
    set_current_draft(None, "")


def to_document_branding() -> DocumentBranding:
    meta = get_document_meta()
    return DocumentBranding(
        header_title=meta.get("header_title", ""),
        module_name=meta.get("module_name", ""),
        project_name=meta.get("project_name", "S4 HANA SANMAR"),
    )


def add_block(block_type: BlockType) -> None:
    st.session_state[BLOCKS_KEY].append(
        {
            "id": uuid.uuid4().hex,
            "type": block_type,
            "payload": _new_payload(block_type),
        }
    )


def remove_block(block_id: str) -> None:
    st.session_state[BLOCKS_KEY] = [b for b in get_blocks() if b["id"] != block_id]


def move_block(block_id: str, direction: int) -> None:
    """direction = -1 for up, +1 for down."""
    blocks = get_blocks()
    idx = next((i for i, b in enumerate(blocks) if b["id"] == block_id), None)
    if idx is None:
        return
    new_idx = idx + direction
    if not 0 <= new_idx < len(blocks):
        return
    blocks[idx], blocks[new_idx] = blocks[new_idx], blocks[idx]


def resize_table(block_id: str, rows: int, cols: int) -> None:
    """Resize the table payload while preserving existing cell text."""
    rows = max(1, int(rows))
    cols = max(1, int(cols))
    for b in get_blocks():
        if b["id"] != block_id:
            continue
        payload = b["payload"]
        old = payload.get("data") or []
        new_data = []
        for r in range(rows):
            row = []
            for c in range(cols):
                if r < len(old) and c < len(old[r]):
                    row.append(old[r][c])
                else:
                    row.append("")
            new_data.append(row)
        payload["rows"] = rows
        payload["cols"] = cols
        payload["data"] = new_data
        return


def import_table_text(block_id: str, pasted_text: str) -> None:
    """Parse pasted tabular text from Excel/Word into a table payload."""
    normalized = (pasted_text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line for line in normalized.split("\n") if line.strip()]
    if not lines:
        return

    split_rows = [line.split("\t") for line in lines]
    width_counts = Counter(len(row) for row in split_rows if len(row) > 1)
    if not width_counts:
        return

    cols = max(width_counts.items(), key=lambda item: (item[1], item[0]))[0]
    table_rows = [row for row in split_rows if len(row) == cols]
    if not table_rows:
        return

    data: List[List[str]] = []
    current_row: List[str] | None = None
    started = False

    for raw_row in split_rows:
        if len(raw_row) == cols:
            row = [cell.strip() for cell in raw_row]
            data.append(row)
            current_row = row
            started = True
            continue

        if not started or current_row is None:
            # Ignore leading descriptive text before the actual table starts.
            continue

        cleaned = [cell.strip() for cell in raw_row]
        non_empty = [(idx, cell) for idx, cell in enumerate(cleaned) if cell]
        if not non_empty:
            continue

        # Word often breaks a wide row into a continuation line with fewer
        # tab-separated cells. Treat that line as a continuation of the prior row.
        for idx, cell in non_empty:
            target_idx = min(idx, cols - 1)
            if current_row[target_idx]:
                current_row[target_idx] = f"{current_row[target_idx]} {cell}".strip()
            else:
                current_row[target_idx] = cell

    rows = len(data)

    for block in get_blocks():
        if block["id"] != block_id:
            continue
        payload = block["payload"]
        payload["rows"] = rows
        payload["cols"] = cols
        payload["data"] = data
        return


def export_project_state() -> Dict[str, Any]:
    """Return a JSON-safe snapshot of the current editor state."""
    blocks_payload: List[Dict[str, Any]] = []
    for block in get_blocks():
        payload = deepcopy(block["payload"])
        if block["type"] == BlockType.IMAGE:
            payload["image_base64"] = _encode_bytes(payload.pop("image_bytes", None))
        blocks_payload.append(
            {
                "id": block["id"],
                "type": block["type"].value,
                "payload": payload,
            }
        )

    doc_meta = deepcopy(get_document_meta())

    return {
        "schema_version": SCHEMA_VERSION,
        "document_meta": doc_meta,
        "blocks": blocks_payload,
    }


def import_project_state(project_data: Dict[str, Any]) -> None:
    """Load a saved editor snapshot into session state."""
    if int(project_data.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError("Unsupported draft schema version.")

    _reset_widget_state()

    document_meta = _default_document_meta()
    incoming_meta = deepcopy(project_data.get("document_meta") or {})
    document_meta.update(incoming_meta)
    st.session_state[DOC_META_KEY] = document_meta

    restored_blocks: List[Dict[str, Any]] = []
    for raw_block in project_data.get("blocks") or []:
        block_type = BlockType(raw_block["type"])
        payload = deepcopy(raw_block.get("payload") or {})
        if block_type == BlockType.IMAGE:
            payload["image_bytes"] = _decode_bytes(payload.pop("image_base64", None))
        restored_blocks.append(
            {
                "id": raw_block.get("id") or uuid.uuid4().hex,
                "type": block_type,
                "payload": payload,
            }
        )
    st.session_state[BLOCKS_KEY] = restored_blocks


def clear_project_state() -> None:
    _reset_widget_state()
    st.session_state[BLOCKS_KEY] = []
    st.session_state[DOC_META_KEY] = _default_document_meta()
    clear_current_draft()
    st.session_state[LAST_SAVED_SNAPSHOT_KEY] = None


def set_last_saved_snapshot(snapshot: Dict[str, Any] | None) -> None:
    st.session_state[LAST_SAVED_SNAPSHOT_KEY] = deepcopy(snapshot) if snapshot else None


def mark_current_state_saved() -> None:
    set_last_saved_snapshot(export_project_state())


def current_project_fingerprint() -> str:
    return json.dumps(export_project_state(), sort_keys=True)


def has_unsaved_changes() -> bool:
    last_snapshot = st.session_state.get(LAST_SAVED_SNAPSHOT_KEY)
    if last_snapshot is None:
        return current_project_fingerprint() != json.dumps(_default_project_state_snapshot(), sort_keys=True)
    return current_project_fingerprint() != json.dumps(last_snapshot, sort_keys=True)


def to_domain_blocks() -> List[Any]:
    """Convert the UI state into the dataclass blocks the builder expects."""
    domain = []
    for b in get_blocks():
        t = b["type"]
        p = b["payload"]
        if t == BlockType.HEADING:
            domain.append(HeadingBlock(text=p.get("text", "")))
        elif t == BlockType.SUBHEADING:
            domain.append(SubheadingBlock(text=p.get("text", "")))
        elif t == BlockType.NORMAL_HEADING:
            domain.append(NormalHeadingBlock(text=p.get("text", "")))
        elif t == BlockType.PARAGRAPH:
            domain.append(ParagraphBlock(text=p.get("text", "")))
        elif t == BlockType.IMAGE:
            domain.append(
                ImageBlock(
                    image_bytes=p.get("image_bytes"),
                    filename=p.get("filename", ""),
                    width_ratio=float(p.get("width_ratio", 0.7)),
                )
            )
        elif t == BlockType.TABLE:
            domain.append(
                TableBlock(
                    rows=int(p.get("rows", 1)),
                    cols=int(p.get("cols", 1)),
                    data=p.get("data", []),
                )
            )
    return domain

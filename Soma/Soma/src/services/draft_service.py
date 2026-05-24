"""
Draft persistence backed by Supabase PostgREST.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from . import supabase_service


TABLE_NAME = "draft_projects"


@dataclass
class DraftSummary:
    draft_id: str
    name: str
    owner_user_id: str
    last_modified_by_user_id: str
    created_at: str
    updated_at: str


@dataclass
class DraftRecord:
    summary: DraftSummary
    project_json: Dict[str, Any]


def _row_to_summary(row: Dict[str, Any]) -> DraftSummary:
    return DraftSummary(
        draft_id=row["id"],
        name=row["name"],
        owner_user_id=row["owner_user_id"],
        last_modified_by_user_id=row["last_modified_by_user_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_drafts() -> List[DraftSummary]:
    rows = supabase_service.request_json(
        "GET",
        f"/rest/v1/{TABLE_NAME}",
        api_key=supabase_service.service_role_key(),
        bearer_token=supabase_service.service_role_key(),
        query={
            "select": "id,name,owner_user_id,last_modified_by_user_id,created_at,updated_at",
            "order": "updated_at.desc",
        },
    ) or []
    return [_row_to_summary(row) for row in rows]


def get_draft(draft_id: str) -> DraftRecord:
    rows = supabase_service.request_json(
        "GET",
        f"/rest/v1/{TABLE_NAME}",
        api_key=supabase_service.service_role_key(),
        bearer_token=supabase_service.service_role_key(),
        query={
            "select": "*",
            "id": f"eq.{draft_id}",
            "limit": "1",
        },
    ) or []
    if not rows:
        raise RuntimeError("Draft not found.")
    row = rows[0]
    return DraftRecord(
        summary=_row_to_summary(row),
        project_json=row["project_json"],
    )


def create_draft(name: str, project_json: Dict[str, Any], user_id: str) -> DraftSummary:
    rows = supabase_service.request_json(
        "POST",
        f"/rest/v1/{TABLE_NAME}",
        api_key=supabase_service.service_role_key(),
        bearer_token=supabase_service.service_role_key(),
        json_body=[
            {
                "name": name,
                "owner_user_id": user_id,
                "last_modified_by_user_id": user_id,
                "project_json": project_json,
            }
        ],
        extra_headers={"Prefer": "return=representation"},
    ) or []
    if not rows:
        raise RuntimeError("Draft was not created.")
    return _row_to_summary(rows[0])


def update_draft(draft_id: str, name: str, project_json: Dict[str, Any], user_id: str) -> DraftSummary:
    rows = supabase_service.request_json(
        "PATCH",
        f"/rest/v1/{TABLE_NAME}",
        api_key=supabase_service.service_role_key(),
        bearer_token=supabase_service.service_role_key(),
        query={"id": f"eq.{draft_id}"},
        json_body={
            "name": name,
            "project_json": project_json,
            "last_modified_by_user_id": user_id,
        },
        extra_headers={"Prefer": "return=representation"},
    ) or []
    if not rows:
        raise RuntimeError("Draft was not updated.")
    return _row_to_summary(rows[0])


def delete_draft(draft_id: str) -> None:
    supabase_service.request_json(
        "DELETE",
        f"/rest/v1/{TABLE_NAME}",
        api_key=supabase_service.service_role_key(),
        bearer_token=supabase_service.service_role_key(),
        query={"id": f"eq.{draft_id}"},
    )

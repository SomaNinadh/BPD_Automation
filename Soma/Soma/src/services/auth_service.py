"""
Supabase Auth helpers for the Streamlit app.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from . import supabase_service


def _field(source: Any, name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


@dataclass
class AuthIdentity:
    user_id: str
    email: str
    access_token: str
    refresh_token: str


def _identity_from_session_payload(payload: Dict[str, Any]) -> AuthIdentity | None:
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    user = payload.get("user") or {}
    user_id = _field(user, "id")
    email = _field(user, "email") or ""
    if not access_token or not refresh_token or not user_id:
        return None
    return AuthIdentity(
        user_id=user_id,
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def sign_up(email: str, password: str) -> tuple[AuthIdentity | None, str]:
    response = supabase_service.request_json(
        "POST",
        "/auth/v1/signup",
        api_key=supabase_service.anon_key(),
        json_body={
            "email": email,
            "password": password,
        },
    )
    identity = _identity_from_session_payload(response or {})
    if identity is not None:
        return identity, "Account created and signed in."
    return None, "Account created. If email confirmation is enabled in Supabase, confirm your email and then sign in."


def sign_in(email: str, password: str) -> AuthIdentity:
    response = supabase_service.request_json(
        "POST",
        "/auth/v1/token",
        api_key=supabase_service.anon_key(),
        query={"grant_type": "password"},
        json_body={
            "email": email,
            "password": password,
        },
    )
    identity = _identity_from_session_payload(response or {})
    if identity is None:
        raise RuntimeError("Unable to create a signed-in session.")
    return identity


def restore_session(access_token: str, refresh_token: str) -> AuthIdentity:
    user = supabase_service.request_json(
        "GET",
        "/auth/v1/user",
        api_key=supabase_service.anon_key(),
        bearer_token=access_token,
    )
    user_id = _field(user, "id")
    email = _field(user, "email") or ""
    if not user_id:
        raise RuntimeError("Unable to restore the signed-in user.")
    return AuthIdentity(
        user_id=user_id,
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def sign_out(access_token: str, refresh_token: str) -> None:
    supabase_service.request_json(
        "POST",
        "/auth/v1/logout",
        api_key=supabase_service.anon_key(),
        bearer_token=access_token,
        json_body={},
    )

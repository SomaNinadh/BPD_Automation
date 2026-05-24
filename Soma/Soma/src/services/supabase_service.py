"""
Supabase HTTP helpers.

Uses the Supabase REST and Auth endpoints directly so the app does not
depend on the `supabase` Python package at runtime.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict
from urllib import error, parse, request

import streamlit as st


def _read_secret(name: str) -> str:
    if name in st.secrets:
        value = str(st.secrets[name]).strip()
        if value:
            return value
    value = os.environ.get(name, "").strip()
    if value:
        return value
    raise RuntimeError(f"Missing required secret: {name}")


def is_configured() -> bool:
    try:
        _read_secret("SUPABASE_URL")
        _read_secret("SUPABASE_ANON_KEY")
        _read_secret("SUPABASE_SERVICE_ROLE_KEY")
        return True
    except RuntimeError:
        return False


def supabase_url() -> str:
    return _read_secret("SUPABASE_URL").rstrip("/")


def anon_key() -> str:
    return _read_secret("SUPABASE_ANON_KEY")


def service_role_key() -> str:
    return _read_secret("SUPABASE_SERVICE_ROLE_KEY")


def _build_url(path: str, query: Dict[str, str] | None = None) -> str:
    url = f"{supabase_url()}{path}"
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    return url


def request_json(
    method: str,
    path: str,
    *,
    api_key: str,
    bearer_token: str | None = None,
    json_body: Dict[str, Any] | list[Dict[str, Any]] | None = None,
    query: Dict[str, str] | None = None,
    extra_headers: Dict[str, str] | None = None,
) -> Any:
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    if extra_headers:
        headers.update(extra_headers)

    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")

    req = request.Request(
        _build_url(path, query),
        data=data,
        headers=headers,
        method=method.upper(),
    )

    try:
        with request.urlopen(req) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
            message = parsed.get("msg") or parsed.get("message") or raw
        except Exception:
            message = raw or str(exc)
        raise RuntimeError(f"Supabase request failed ({exc.code}): {message}") from exc

from __future__ import annotations

import json
from typing import Any
from urllib import request

from namel3ss_safeio import safe_urlopen


def get_json(payload: dict) -> dict:
    url = _require_text(payload, "url")
    headers = _read_headers(payload)
    timeout_seconds = _read_timeout(payload)
    return _request_json("GET", url, headers=headers, data=None, timeout_seconds=timeout_seconds)


def post_json(payload: dict) -> dict:
    url = _require_text(payload, "url")
    headers = _read_headers(payload)
    timeout_seconds = _read_timeout(payload)
    body = payload.get("data", {})
    if not isinstance(body, (dict, list)):
        raise ValueError("payload.data must be an object or list")
    data = json.dumps(body).encode("utf-8")
    headers.setdefault("Content-Type", "application/json")
    return _request_json("POST", url, headers=headers, data=data, timeout_seconds=timeout_seconds)


def _request_json(method: str, url: str, *, headers: dict[str, str], data: bytes | None, timeout_seconds: int) -> dict:
    req = request.Request(url, method=method, headers=headers, data=data)
    with safe_urlopen(req, timeout=timeout_seconds) as resp:
        status = getattr(resp, "status", None) or resp.getcode()
        raw = resp.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as err:
            raise ValueError("Response was not valid JSON") from err
        return {
            "status": int(status),
            "headers": dict(resp.headers.items()),
            "data": parsed,
        }


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"payload.{key} must be a non-empty string")
    return value.strip()


def _read_headers(payload: dict) -> dict[str, str]:
    headers = payload.get("headers", {})
    if headers is None:
        return {}
    if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()):
        raise ValueError("payload.headers must be an object of string headers")
    return dict(headers)


def _read_timeout(payload: dict) -> int:
    value: Any = payload.get("timeout_seconds", 10)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("payload.timeout_seconds must be a number")
    seconds = int(value)
    if seconds <= 0:
        raise ValueError("payload.timeout_seconds must be positive")
    return seconds


__all__ = ["get_json", "post_json"]

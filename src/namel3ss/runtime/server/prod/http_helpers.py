from __future__ import annotations

import json
from typing import Any

from namel3ss.utils.json_tools import dumps as json_dumps


def respond_json(
    handler: Any,
    payload: dict,
    *,
    status: int = 200,
    sort_keys: bool = False,
    headers: dict[str, str] | None = None,
) -> None:
    data = json_dumps(payload, sort_keys=sort_keys).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    if headers:
        for key, value in headers.items():
            handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(data)


def respond_bytes(
    handler: Any,
    payload: bytes,
    *,
    status: int = 200,
    content_type: str = "application/octet-stream",
    headers: dict[str, str] | None = None,
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    if headers:
        for key, value in headers.items():
            handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(payload)


def read_json_body(handler: Any) -> dict | None:
    length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(length) if length else b""
    if not raw_body:
        return {}
    try:
        decoded = raw_body.decode("utf-8")
        return json.loads(decoded or "{}")
    except Exception:
        return None


def static_cache_headers(path: str, content_type: str) -> dict[str, str]:
    normalized_path = (path or "").lower()
    normalized_type = (content_type or "").lower()
    is_shell_html = normalized_path in {"/", "/index.html"} or normalized_type.startswith("text/html")
    is_runtime_script = normalized_path.endswith(".js")
    is_runtime_style = normalized_path.endswith(".css")
    is_icon_svg = normalized_path.startswith("/icons/") and normalized_path.endswith(".svg")
    if is_shell_html or is_runtime_script or is_runtime_style or is_icon_svg:
        return {
            "Cache-Control": "no-store, max-age=0, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    return {}


__all__ = ["read_json_body", "respond_bytes", "respond_json", "static_cache_headers"]

from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.studio.security_api import apply_security_override, apply_security_sandbox


def handle_security_override(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="security"), status=400)
        return
    try:
        resp = apply_security_override(handler.server.app_path, body)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="security", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_security_sandbox(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="security"), status=400)
        return
    try:
        resp = apply_security_sandbox(handler.server.app_path, body)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="security", source=source)
        handler._respond_json(payload, status=400)
        return


__all__ = ["handle_security_override", "handle_security_sandbox"]

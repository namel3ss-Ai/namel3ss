from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception
from namel3ss.studio.trust_api import apply_trust_verify


def handle_trust_verify(handler: Any, source: str, body: dict) -> None:
    try:
        payload = apply_trust_verify(handler.server.app_path, body)  # type: ignore[attr-defined]
        status = 200 if payload.get("status") != "error" else 400
        handler._respond_json(payload, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="trust", source=source)
        handler._respond_json(payload, status=400)
        return


__all__ = ["handle_trust_verify"]

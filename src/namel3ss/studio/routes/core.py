from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.studio.api import execute_action


def handle_action(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="engine"), status=400)
        return
    action_id = body.get("id")
    payload = body.get("payload") or {}
    if not isinstance(action_id, str):
        handler._respond_json(build_error_payload("Action id is required", kind="engine"), status=400)
        return
    if not isinstance(payload, dict):
        handler._respond_json(build_error_payload("Payload must be an object", kind="engine"), status=400)
        return
    try:
        resp = execute_action(source, handler._get_session(), action_id, payload, handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(resp, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="engine", source=source)
        handler._respond_json(payload, status=400)
        return
    except Exception as err:  # pragma: no cover - defensive guard rail
        payload = build_error_payload(str(err), kind="internal")
        handler._respond_json(payload, status=500)
        return


__all__ = ["handle_action"]

from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.router.streaming import build_sse_body, sorted_yield_messages
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
        resp = execute_action(
            source,
            handler._get_session(),
            action_id,
            payload,
            handler.server.app_path,  # type: ignore[attr-defined]
            headers=dict(handler.headers.items()),
        )
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


def handle_action_stream(handler: Any, source: str, body: dict) -> None:
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
        response = execute_action(
            source,
            handler._get_session(),
            action_id,
            payload,
            handler.server.app_path,  # type: ignore[attr-defined]
            headers=dict(handler.headers.items()),
        )
    except Namel3ssError as err:
        response = build_error_from_exception(err, kind="engine", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        response = build_error_payload(str(err), kind="internal")
    if not isinstance(response, dict):
        response = {"ok": False, "error": "Unexpected action response", "kind": "internal"}
    body_bytes = build_sse_body(
        sorted_yield_messages(response.get("yield_messages")),
        response,
    )
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Content-Length", str(len(body_bytes)))
    handler.end_headers()
    handler.wfile.write(body_bytes)


__all__ = ["handle_action", "handle_action_stream"]

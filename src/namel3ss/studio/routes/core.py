from __future__ import annotations

from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.studio.api import apply_edit, apply_tool_wizard, apply_tools_auto_bind, execute_action


def handle_edit(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="edit"), status=400)
        return
    op = body.get("op")
    target = body.get("target")
    value = body.get("value", "")
    if not isinstance(op, str):
        handler._respond_json(build_error_payload("Edit op is required", kind="edit"), status=400)
        return
    if not isinstance(target, dict):
        handler._respond_json(build_error_payload("Edit target is required", kind="edit"), status=400)
        return
    if op in {"set_title", "set_text", "set_button_label"} and not isinstance(value, str):
        handler._respond_json(build_error_payload("Edit value must be a string", kind="edit"), status=400)
        return
    try:
        resp = apply_edit(handler.server.app_path, op, target, value, handler._get_session())  # type: ignore[attr-defined]
        handler._respond_json(resp, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="edit", source=source)
        handler._respond_json(payload, status=400)
        return


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


def handle_tool_wizard(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="tool_wizard"), status=400)
        return
    try:
        resp = apply_tool_wizard(handler.server.app_path, body)  # type: ignore[attr-defined]
        handler._respond_json(resp, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="tool_wizard", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_theme(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict) or "value" not in body:
        handler._respond_json(build_error_payload("Theme value required", kind="engine"), status=400)
        return
    value = body.get("value")
    if value not in {"light", "dark", "system"}:
        handler._respond_json(build_error_payload("Theme must be light, dark, or system.", kind="engine"), status=400)
        return
    session = handler._get_session()
    try:
        from namel3ss.studio.theme import apply_runtime_theme

        resp = apply_runtime_theme(source, session, value, handler.server.app_path)  # type: ignore[attr-defined]
        handler._respond_json(resp, status=200)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="engine", source=source)
        handler._respond_json(payload, status=400)
        return


def handle_reset(handler: Any) -> None:
    session = handler._get_session()
    store = getattr(session, "store", None)
    if store is not None:
        try:
            store.clear()
        except Exception as err:  # pragma: no cover - defensive
            payload = build_error_payload(f"Unable to reset store: {err}", kind="engine")
            handler._respond_json(payload, status=500)
            return
        handler.server.session_state = type(session)(store=store)  # type: ignore[attr-defined]
    else:
        handler.server.session_state = type(session)()  # type: ignore[attr-defined]
    handler._respond_json({"ok": True}, status=200)


def handle_tools_auto_bind(handler: Any, source: str, body: dict) -> None:
    if not isinstance(body, dict):
        handler._respond_json(build_error_payload("Body must be a JSON object", kind="tools"), status=400)
        return
    try:
        resp = apply_tools_auto_bind(source, handler.server.app_path)  # type: ignore[attr-defined]
        status = 200 if resp.get("ok", True) else 400
        handler._respond_json(resp, status=status)
        return
    except Namel3ssError as err:
        payload = build_error_from_exception(err, kind="tools", source=source)
        handler._respond_json(payload, status=400)
        return


__all__ = [
    "handle_action",
    "handle_edit",
    "handle_reset",
    "handle_theme",
    "handle_tool_wizard",
    "handle_tools_auto_bind",
]

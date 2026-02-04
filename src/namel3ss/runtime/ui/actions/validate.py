from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.ui.actions.model import SUBMIT_RESERVED_KEYS
from namel3ss.utils.json_tools import dumps as json_dumps


def ensure_json_serializable(data: dict) -> None:
    try:
        json_dumps(data)
    except Exception as exc:  # pragma: no cover - guard rail
        raise Namel3ssError(f"Response is not JSON-serializable: {exc}")


def normalize_submit_payload(payload: dict | None) -> dict:
    payload = payload or {}
    if not isinstance(payload, dict):
        raise Namel3ssError(submit_payload_type_message())
    if "values" in payload:
        if not isinstance(payload.get("values"), dict):
            raise Namel3ssError(missing_values_message({"values"}))
        return payload
    reserved = {key for key in payload if key in SUBMIT_RESERVED_KEYS}
    if reserved:
        raise Namel3ssError(missing_values_message(reserved))
    return {"values": payload}


def submit_payload_type_message() -> str:
    return build_guidance_message(
        what="Submit form payload was not a JSON object.",
        why="Form submissions need a dictionary of field values; numbers, strings, or lists cannot be mapped to fields.",
        fix='Send {"values": {...}} or a flat object that can be wrapped automatically.',
        example='{"values":{"email":"ada@example.com"}} (or {"email":"ada@example.com"})',
    )


def missing_values_message(reserved_keys: set[str]) -> str:
    reserved_note = f" Payload included reserved keys: {', '.join(sorted(reserved_keys))}." if reserved_keys else ""
    return build_guidance_message(
        what="Submit form payload is missing a 'values' object.",
        why="Form submissions read values from the 'values' key; other top-level keys are ignored." + reserved_note,
        fix='Send {"values": {...}} or pass a flat object so it can be wrapped automatically.',
        example='{"values":{"email":"ada@example.com"}} (or {"email":"ada@example.com"})',
    )


def action_payload_message() -> str:
    return build_guidance_message(
        what="Action payload was not a JSON object.",
        why="UI actions expect a dictionary of inputs; arrays, numbers, or strings cannot be unpacked into fields.",
        fix='Send {} for empty payloads or pass an object like {"values":{"name":"Ada"}}.',
        example='n3 app.ai page.home.button.run "{}"',
    )


def text_input_missing_message(field_name: str) -> str:
    return build_guidance_message(
        what=f'Text input payload is missing "{field_name}".',
        why="Text inputs send a single text value using the declared input name.",
        fix=f'Send {{"{field_name}": "<text>"}} as the payload.',
        example=f'n3 app.ai <action_id> {{"{field_name}": "hello"}}',
    )


def text_input_type_message(field_name: str) -> str:
    return build_guidance_message(
        what=f'Text input "{field_name}" must be text.',
        why="Text inputs accept a single line of text and pass it directly to the flow.",
        fix=f'Send {{"{field_name}": "<text>"}} as the payload.',
        example=f'n3 app.ai <action_id> {{"{field_name}": "hello"}}',
    )


def unknown_action_message(action_id: str, actions: Dict[str, dict]) -> str:
    available = sorted(actions.keys())
    sample = ", ".join(available[:5]) if available else "none"
    if len(available) > 5:
        sample += ", …"
    why = f"The manifest exposes actions: {sample}." if available else "No actions were generated for this app."
    example = f"n3 app.ai {available[0]} {{}}" if available else "n3 app.ai actions"
    return build_guidance_message(
        what=f"Unknown action '{action_id}'.",
        why=why,
        fix="Use an action id from `n3 app.ai actions` or define the action in app.ai.",
        example=example,
    )


def action_disabled_message(action_id: str, predicate: str | None = None) -> str:
    rule = f" because {predicate}" if predicate else ""
    return build_guidance_message(
        what=f"Action '{action_id}' is disabled.",
        why=f"The action is disabled by an availability rule{rule}.",
        fix="Update state to satisfy the rule or remove the only-when clause.",
        example=f'n3 app.ai {action_id} "{{}}"',
    )


__all__ = [
    "action_payload_message",
    "action_disabled_message",
    "ensure_json_serializable",
    "missing_values_message",
    "normalize_submit_payload",
    "submit_payload_type_message",
    "text_input_missing_message",
    "text_input_type_message",
    "unknown_action_message",
]

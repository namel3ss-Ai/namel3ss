from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.triggers import list_triggers, load_trigger_config, register_trigger, save_trigger_config


def get_triggers_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    entries = load_trigger_config(app_file.parent, app_file)
    rows = list_triggers(entries)
    return {
        "ok": True,
        "count": len(rows),
        "items": rows,
    }


def apply_triggers_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    action = _text(body.get("action")) or "list"
    if action == "list":
        return get_triggers_payload(app_path)
    if action != "register":
        raise Namel3ssError(_unknown_action_message(action))

    trigger_type = _required_text(body.get("type"), "type")
    name = _required_text(body.get("name"), "name")
    pattern = _required_text(body.get("pattern"), "pattern")
    flow = _required_text(body.get("flow"), "flow")
    filters = body.get("filters")

    app_file = Path(app_path)
    config = load_trigger_config(app_file.parent, app_file)
    updated = register_trigger(
        config,
        trigger_type=trigger_type,
        name=name,
        pattern=pattern,
        flow=flow,
        filters=filters if isinstance(filters, dict) else None,
    )
    out_path = save_trigger_config(app_file.parent, app_file, updated)
    payload = get_triggers_payload(app_path)
    payload["action"] = "register"
    payload["output_path"] = out_path.as_posix()
    return payload


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _required_text(value: object, label: str) -> str:
    text = _text(value)
    if text:
        return text
    raise Namel3ssError(_missing_value_message(label))


def _missing_value_message(label: str) -> str:
    return build_guidance_message(
        what=f"{label} is required.",
        why=f"Trigger actions require {label}.",
        fix=f"Provide {label} and retry.",
        example='{"action":"register","type":"webhook","name":"payment_received","pattern":"/hooks/payment","flow":"process_payment"}',
    )


def _unknown_action_message(action: str) -> str:
    return build_guidance_message(
        what=f"Unknown trigger action '{action}'.",
        why="Supported actions are list and register.",
        fix="Use one of the supported action values.",
        example='{"action":"list"}',
    )


__all__ = ["apply_triggers_payload", "get_triggers_payload"]

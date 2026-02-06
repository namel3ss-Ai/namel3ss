from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.feature_gate import require_app_capability
from namel3ss.versioning import (
    add_version,
    deprecate_version,
    list_versions,
    load_version_config,
    parse_entity_ref,
    remove_version,
    save_version_config,
)


def get_versioning_payload(app_path: str) -> dict[str, object]:
    app_file = Path(app_path)
    require_app_capability(app_file, "versioning_quality_mlops")
    config = load_version_config(app_file.parent, app_file)
    items = list_versions(config)
    deprecated = [item for item in items if str(item.get("status")) == "deprecated"]
    removed = [item for item in items if str(item.get("status")) == "removed"]
    return {
        "ok": True,
        "count": len(items),
        "deprecated_count": len(deprecated),
        "removed_count": len(removed),
        "items": items,
    }


def apply_versioning_payload(source: str, body: dict, app_path: str) -> dict[str, object]:
    _ = source
    app_file = Path(app_path)
    require_app_capability(app_file, "versioning_quality_mlops", source_override=source)
    config = load_version_config(app_file.parent, app_file)
    action = _text(body.get("action")) or "list"

    if action == "list":
        return get_versioning_payload(app_path)

    entity = _required_text(body.get("entity"), "entity")
    version = _required_text(body.get("version"), "version")
    kind, name = parse_entity_ref(entity)

    if action == "add":
        updated = add_version(
            config,
            kind=kind,
            entity_name=name,
            version=version,
            target=_text(body.get("target")) or None,
            status=_text(body.get("status")) or "active",
            replacement=_text(body.get("replacement")) or None,
            deprecation_date=_text(body.get("deprecation_date")) or None,
        )
    elif action == "deprecate":
        updated = deprecate_version(
            config,
            kind=kind,
            entity_name=name,
            version=version,
            replacement=_text(body.get("replacement")) or None,
            deprecation_date=_text(body.get("deprecation_date")) or None,
        )
    elif action == "remove":
        updated = remove_version(
            config,
            kind=kind,
            entity_name=name,
            version=version,
            replacement=_text(body.get("replacement")) or None,
        )
    else:
        raise Namel3ssError(_unknown_action_message(action))

    out_path = save_version_config(app_file.parent, app_file, updated)
    payload = get_versioning_payload(app_path)
    payload["action"] = action
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
        why=f"Versioning action requires {label}.",
        fix=f"Provide {label} and retry.",
        example='{"action":"add","entity":"flow:summarise","version":"2.0"}',
    )


def _unknown_action_message(action: str) -> str:
    return build_guidance_message(
        what=f"Unknown versioning action '{action}'.",
        why="Supported actions are list, add, deprecate, and remove.",
        fix="Use one of the supported action values.",
        example='{"action":"list"}',
    )


__all__ = ["apply_versioning_payload", "get_versioning_payload"]

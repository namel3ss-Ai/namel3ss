from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


TRIGGERS_FILENAME = "triggers.yaml"
TRIGGER_TYPES = ("queue", "timer", "upload", "webhook")
_PATTERN_KEYS = {
    "webhook": "path",
    "upload": "directory",
    "timer": "cron",
    "queue": "pattern",
}


@dataclass(frozen=True)
class TriggerConfig:
    type: str
    name: str
    flow: str
    pattern: str
    filters: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        pattern_key = _PATTERN_KEYS[self.type]
        payload: dict[str, object] = {
            "name": self.name,
            pattern_key: self.pattern,
            "flow": self.flow,
        }
        if self.filters:
            payload["filters"] = dict(sorted(self.filters.items(), key=lambda item: str(item[0])))
        return payload


def triggers_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / TRIGGERS_FILENAME


def load_trigger_config(project_root: str | Path | None, app_path: str | Path | None) -> list[TriggerConfig]:
    path = triggers_path(project_root, app_path)
    if path is None or not path.exists():
        return []
    try:
        raw_payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_file_message(path, str(err))) from err
    if not isinstance(raw_payload, dict):
        raise Namel3ssError(_invalid_file_message(path, "top-level value must be a map"))
    triggers: list[TriggerConfig] = []
    for trigger_type in sorted(raw_payload.keys(), key=lambda item: str(item)):
        if trigger_type not in TRIGGER_TYPES:
            raise Namel3ssError(_unknown_trigger_type_message(str(trigger_type)))
        rows = raw_payload.get(trigger_type)
        if rows is None:
            continue
        if not isinstance(rows, list):
            raise Namel3ssError(_invalid_file_message(path, f"section '{trigger_type}' must be a list"))
        for row in rows:
            if not isinstance(row, dict):
                raise Namel3ssError(_invalid_file_message(path, f"section '{trigger_type}' has non-object item"))
            triggers.append(_trigger_from_row(str(trigger_type), row))
    return _sorted_triggers(triggers)


def save_trigger_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    triggers: list[TriggerConfig],
) -> Path:
    path = triggers_path(project_root, app_path)
    if path is None:
        raise Namel3ssError(_missing_path_message())
    payload: dict[str, object] = {}
    for trigger_type in TRIGGER_TYPES:
        payload[trigger_type] = []
    for trigger in _sorted_triggers(triggers):
        section = payload.setdefault(trigger.type, [])
        if isinstance(section, list):
            section.append(trigger.to_dict())
    # remove empty sections to keep file concise
    compact = {name: rows for name, rows in payload.items() if rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(compact), encoding="utf-8")
    return path


def register_trigger(
    triggers: list[TriggerConfig],
    *,
    trigger_type: str,
    name: str,
    pattern: str,
    flow: str,
    filters: dict[str, object] | None = None,
) -> list[TriggerConfig]:
    normalized = TriggerConfig(
        type=_normalize_trigger_type(trigger_type),
        name=_require_text(name, "name"),
        flow=_require_text(flow, "flow"),
        pattern=_require_text(pattern, "pattern"),
        filters=_normalize_filters(filters),
    )
    out: list[TriggerConfig] = []
    replaced = False
    for item in triggers:
        if item.type == normalized.type and item.name == normalized.name:
            if not replaced:
                out.append(normalized)
                replaced = True
            continue
        out.append(item)
    if not replaced:
        out.append(normalized)
    return _sorted_triggers(out)


def list_triggers(triggers: list[TriggerConfig]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trigger in _sorted_triggers(triggers):
        row = {
            "type": trigger.type,
            "name": trigger.name,
            "flow": trigger.flow,
            "pattern": trigger.pattern,
        }
        if trigger.filters:
            row["filters"] = dict(sorted(trigger.filters.items(), key=lambda item: str(item[0])))
        rows.append(row)
    return rows


def _trigger_from_row(trigger_type: str, row: dict[str, object]) -> TriggerConfig:
    pattern = _read_pattern(trigger_type, row)
    return TriggerConfig(
        type=trigger_type,
        name=_require_text(row.get("name"), "name"),
        flow=_require_text(row.get("flow"), "flow"),
        pattern=pattern,
        filters=_normalize_filters(row.get("filters")),
    )


def _read_pattern(trigger_type: str, row: dict[str, object]) -> str:
    key = _PATTERN_KEYS[trigger_type]
    value = row.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if key != "pattern":
        fallback = row.get("pattern")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()
    raise Namel3ssError(_missing_field_message(key))


def _normalize_trigger_type(value: object) -> str:
    trigger_type = str(value or "").strip().lower()
    if trigger_type in TRIGGER_TYPES:
        return trigger_type
    raise Namel3ssError(_unknown_trigger_type_message(trigger_type))


def _normalize_filters(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_filters_message())
    cleaned: dict[str, object] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        key_text = str(key).strip()
        if not key_text:
            continue
        cleaned[key_text] = value[key]
    return cleaned or None


def _sorted_triggers(values: list[TriggerConfig]) -> list[TriggerConfig]:
    return sorted(
        values,
        key=lambda item: (
            item.type,
            item.name,
            item.pattern,
            item.flow,
            _render_filters(item.filters),
        ),
    )


def _render_filters(filters: dict[str, object] | None) -> str:
    if not filters:
        return ""
    parts = [f"{key}={filters[key]}" for key in sorted(filters.keys(), key=lambda item: str(item))]
    return "|".join(parts)


def _require_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(_missing_field_message(label))


def _missing_field_message(label: str) -> str:
    return build_guidance_message(
        what=f"{label} is required.",
        why=f"Trigger definitions need '{label}'.",
        fix=f"Set '{label}' in triggers.yaml or in the trigger command.",
        example='{"type":"webhook","name":"payment_received","pattern":"/hooks/payments","flow":"process_payment"}',
    )


def _missing_path_message() -> str:
    return build_guidance_message(
        what="Trigger config path is missing.",
        why="Project root could not be resolved.",
        fix="Run this command from a project containing app.ai.",
        example="n3 trigger list",
    )


def _unknown_trigger_type_message(trigger_type: str) -> str:
    allowed = ", ".join(TRIGGER_TYPES)
    return build_guidance_message(
        what=f"Unknown trigger type '{trigger_type}'.",
        why=f"Supported types are: {allowed}.",
        fix="Use webhook, upload, timer, or queue.",
        example='{"type":"timer","name":"nightly","pattern":"0 0 * * *","flow":"cleanup"}',
    )


def _invalid_file_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Trigger config file is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Correct triggers.yaml and try again.",
        example="webhook:\n  - name: payment_received\n    path: /hooks/payment\n    flow: process_payment",
    )


def _invalid_filters_message() -> str:
    return build_guidance_message(
        what="Trigger filters must be an object.",
        why="Filters map keys to values.",
        fix="Use key/value pairs in filters.",
        example='{"source":"billing","priority":"high"}',
    )


__all__ = [
    "TRIGGERS_FILENAME",
    "TRIGGER_TYPES",
    "TriggerConfig",
    "list_triggers",
    "load_trigger_config",
    "register_trigger",
    "save_trigger_config",
    "triggers_path",
]

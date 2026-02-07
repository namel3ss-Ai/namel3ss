from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError

ALLOWED_PROP_TYPES = ("string", "number", "boolean", "state_path")


@dataclass(frozen=True)
class UIPluginPropSpec:
    name: str
    type_name: str
    required: bool


@dataclass(frozen=True)
class UIPluginComponentSchema:
    name: str
    props: dict[str, UIPluginPropSpec]
    events: tuple[str, ...]


@dataclass(frozen=True)
class UIPluginSchema:
    name: str
    module_path: Path
    components: tuple[UIPluginComponentSchema, ...]
    capabilities: tuple[str, ...] = tuple()
    version: str | None = None


def parse_plugin_manifest(payload: object, *, source_path: Path, plugin_root: Path) -> UIPluginSchema:
    if not isinstance(payload, dict):
        raise Namel3ssError(_manifest_error(source_path, "manifest root must be a mapping"))

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Namel3ssError(_manifest_error(source_path, "name must be a non-empty string"))
    normalized_name = name.strip()

    module_value = payload.get("module")
    if not isinstance(module_value, str) or not module_value.strip():
        raise Namel3ssError(_manifest_error(source_path, "module must be a non-empty string"))
    module_path = (plugin_root / module_value).resolve()

    components_value = payload.get("components")
    if not isinstance(components_value, list) or not components_value:
        raise Namel3ssError(_manifest_error(source_path, "components must be a non-empty list"))

    components: list[UIPluginComponentSchema] = []
    seen_components: set[str] = set()
    for idx, entry in enumerate(components_value):
        schema = _parse_component(entry, source_path=source_path, index=idx)
        if schema.name in seen_components:
            raise Namel3ssError(_manifest_error(source_path, f"component '{schema.name}' is declared more than once"))
        seen_components.add(schema.name)
        components.append(schema)

    capabilities = _parse_capabilities(payload.get("capabilities"), source_path=source_path)
    version = payload.get("version")
    if version is not None and not isinstance(version, str):
        raise Namel3ssError(_manifest_error(source_path, "version must be a string when provided"))

    return UIPluginSchema(
        name=normalized_name,
        module_path=module_path,
        components=tuple(components),
        capabilities=capabilities,
        version=version,
    )


def _parse_component(entry: object, *, source_path: Path, index: int) -> UIPluginComponentSchema:
    if not isinstance(entry, dict):
        raise Namel3ssError(_manifest_error(source_path, f"components[{index}] must be a mapping"))

    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Namel3ssError(_manifest_error(source_path, f"components[{index}].name must be a non-empty string"))
    component_name = name.strip()

    props_entry = entry.get("props") or {}
    if not isinstance(props_entry, dict):
        raise Namel3ssError(_manifest_error(source_path, f"components[{index}].props must be a mapping"))

    props: dict[str, UIPluginPropSpec] = {}
    for prop_name, raw_spec in props_entry.items():
        if not isinstance(prop_name, str) or not prop_name.strip():
            raise Namel3ssError(_manifest_error(source_path, f"components[{index}].props keys must be non-empty strings"))
        normalized_prop = prop_name.strip()
        type_name, required = _parse_prop_spec(raw_spec, source_path=source_path, index=index, prop_name=normalized_prop)
        props[normalized_prop] = UIPluginPropSpec(name=normalized_prop, type_name=type_name, required=required)

    events_entry = entry.get("events") or []
    if not isinstance(events_entry, list):
        raise Namel3ssError(_manifest_error(source_path, f"components[{index}].events must be a list"))
    events: list[str] = []
    seen_events: set[str] = set()
    for event_idx, raw_event in enumerate(events_entry):
        if not isinstance(raw_event, str) or not raw_event.strip():
            raise Namel3ssError(_manifest_error(source_path, f"components[{index}].events[{event_idx}] must be a non-empty string"))
        event_name = raw_event.strip()
        if event_name in seen_events:
            raise Namel3ssError(_manifest_error(source_path, f"components[{index}] event '{event_name}' is duplicated"))
        if event_name in props:
            raise Namel3ssError(
                _manifest_error(source_path, f"components[{index}] cannot declare '{event_name}' as both prop and event")
            )
        seen_events.add(event_name)
        events.append(event_name)

    return UIPluginComponentSchema(name=component_name, props=props, events=tuple(events))


def _parse_prop_spec(raw_spec: object, *, source_path: Path, index: int, prop_name: str) -> tuple[str, bool]:
    if isinstance(raw_spec, str):
        type_name = raw_spec.strip().lower()
        required = True
    elif isinstance(raw_spec, dict):
        raw_type = raw_spec.get("type")
        if not isinstance(raw_type, str) or not raw_type.strip():
            raise Namel3ssError(
                _manifest_error(source_path, f"components[{index}].props.{prop_name}.type must be a non-empty string")
            )
        type_name = raw_type.strip().lower()
        required_value = raw_spec.get("required", True)
        if not isinstance(required_value, bool):
            raise Namel3ssError(
                _manifest_error(source_path, f"components[{index}].props.{prop_name}.required must be true or false")
            )
        required = required_value
    else:
        raise Namel3ssError(
            _manifest_error(source_path, f"components[{index}].props.{prop_name} must be a string or mapping")
        )

    if type_name not in ALLOWED_PROP_TYPES:
        allowed = ", ".join(ALLOWED_PROP_TYPES)
        raise Namel3ssError(
            _manifest_error(
                source_path,
                f"components[{index}].props.{prop_name}.type must be one of: {allowed}",
            )
        )
    return type_name, required


def _parse_capabilities(raw_value: object, *, source_path: Path) -> tuple[str, ...]:
    if raw_value is None:
        return tuple()
    if not isinstance(raw_value, list):
        raise Namel3ssError(_manifest_error(source_path, "capabilities must be a list"))
    values: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(raw_value):
        if not isinstance(item, str) or not item.strip():
            raise Namel3ssError(_manifest_error(source_path, f"capabilities[{idx}] must be a non-empty string"))
        token = item.strip().lower()
        if token in seen:
            continue
        seen.add(token)
        values.append(token)
    return tuple(values)


def _manifest_error(source_path: Path, detail: str) -> str:
    return f"Invalid UI plugin manifest '{source_path.as_posix()}': {detail}."


__all__ = [
    "ALLOWED_PROP_TYPES",
    "UIPluginComponentSchema",
    "UIPluginPropSpec",
    "UIPluginSchema",
    "parse_plugin_manifest",
]

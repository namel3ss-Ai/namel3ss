from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.plugin.permissions import parse_extension_permissions

ALLOWED_PROP_TYPES = ("string", "number", "boolean", "state_path")
ALLOWED_HOOK_TYPES = ("compiler", "runtime", "studio")
CURRENT_EXTENSION_API_VERSION = 1


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
    plugin_root: Path
    module_path: Path
    components: tuple[UIPluginComponentSchema, ...]
    capabilities: tuple[str, ...] = tuple()
    permissions: tuple[str, ...] = ("legacy_full_access",)
    hooks: tuple[tuple[str, str], ...] = tuple()
    min_api_version: int = CURRENT_EXTENSION_API_VERSION
    author: str | None = None
    description: str | None = None
    signature: str | None = None
    tags: tuple[str, ...] = tuple()
    rating: float | None = None
    version: str | None = None


def parse_plugin_manifest(payload: object, *, source_path: Path, plugin_root: Path) -> UIPluginSchema:
    if not isinstance(payload, dict):
        raise Namel3ssError(_manifest_error(source_path, "manifest root must be a mapping"))

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise Namel3ssError(_manifest_error(source_path, "name must be a non-empty string"))
    normalized_name = name.strip()

    hooks = _parse_hooks(payload.get("hooks"), source_path=source_path)
    module_value = payload.get("module")
    module_path = _resolve_module_path(
        module_value,
        source_path=source_path,
        plugin_root=plugin_root,
    )

    components_value = payload.get("components", [])
    if not isinstance(components_value, list):
        raise Namel3ssError(_manifest_error(source_path, "components must be a list"))

    components: list[UIPluginComponentSchema] = []
    seen_components: set[str] = set()
    for idx, entry in enumerate(components_value):
        schema = _parse_component(entry, source_path=source_path, index=idx)
        if schema.name in seen_components:
            raise Namel3ssError(_manifest_error(source_path, f"component '{schema.name}' is declared more than once"))
        seen_components.add(schema.name)
        components.append(schema)
    if not components and not hooks:
        raise Namel3ssError(
            _manifest_error(source_path, "manifest must declare at least one component or one hook")
        )
    if components and not isinstance(module_value, str):
        raise Namel3ssError(_manifest_error(source_path, "module must be a non-empty string when components are present"))

    capabilities = _parse_capabilities(payload.get("capabilities"), source_path=source_path)
    permissions = parse_extension_permissions(
        payload.get("permissions"),
        source_label=source_path.as_posix(),
        default_legacy=True,
    )
    min_api_version = _parse_min_api_version(payload.get("min_api_version"), source_path=source_path)
    author = _optional_text(payload.get("author"), source_path=source_path, field="author")
    description = _optional_text(payload.get("description"), source_path=source_path, field="description")
    signature = _optional_text(payload.get("signature"), source_path=source_path, field="signature")
    tags = _parse_tags(payload.get("tags"), source_path=source_path)
    rating = _parse_rating(payload.get("rating"), source_path=source_path)
    version = payload.get("version")
    if version is not None and not isinstance(version, str):
        raise Namel3ssError(_manifest_error(source_path, "version must be a string when provided"))

    return UIPluginSchema(
        name=normalized_name,
        plugin_root=plugin_root.resolve(),
        module_path=module_path,
        components=tuple(components),
        capabilities=capabilities,
        permissions=permissions,
        hooks=hooks,
        min_api_version=min_api_version,
        author=author,
        description=description,
        signature=signature,
        tags=tags,
        rating=rating,
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


def _parse_hooks(raw_value: object, *, source_path: Path) -> tuple[tuple[str, str], ...]:
    if raw_value is None:
        return tuple()
    if not isinstance(raw_value, dict):
        raise Namel3ssError(_manifest_error(source_path, "hooks must be a mapping"))
    values: list[tuple[str, str]] = []
    for key in sorted(raw_value.keys()):
        if not isinstance(key, str):
            raise Namel3ssError(_manifest_error(source_path, "hooks keys must be strings"))
        hook_type = key.strip().lower()
        if hook_type not in ALLOWED_HOOK_TYPES:
            raise Namel3ssError(
                _manifest_error(
                    source_path,
                    f"hooks.{hook_type} is unsupported (allowed: {', '.join(ALLOWED_HOOK_TYPES)})",
                )
            )
        entry = raw_value.get(key)
        if not isinstance(entry, str) or not entry.strip():
            raise Namel3ssError(_manifest_error(source_path, f"hooks.{hook_type} must be a non-empty string"))
        values.append((hook_type, entry.strip()))
    return tuple(values)


def _parse_min_api_version(raw_value: object, *, source_path: Path) -> int:
    if raw_value is None:
        return CURRENT_EXTENSION_API_VERSION
    if not isinstance(raw_value, int):
        raise Namel3ssError(_manifest_error(source_path, "min_api_version must be an integer"))
    if raw_value < 1:
        raise Namel3ssError(_manifest_error(source_path, "min_api_version must be >= 1"))
    if raw_value > CURRENT_EXTENSION_API_VERSION:
        raise Namel3ssError(
            _manifest_error(
                source_path,
                f"min_api_version={raw_value} is newer than supported version {CURRENT_EXTENSION_API_VERSION}",
            )
        )
    return raw_value


def _optional_text(raw_value: object, *, source_path: Path, field: str) -> str | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        raise Namel3ssError(_manifest_error(source_path, f"{field} must be a string when provided"))
    value = raw_value.strip()
    return value or None


def _parse_tags(raw_value: object, *, source_path: Path) -> tuple[str, ...]:
    if raw_value is None:
        return tuple()
    if not isinstance(raw_value, list):
        raise Namel3ssError(_manifest_error(source_path, "tags must be a list when provided"))
    values: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(raw_value):
        if not isinstance(item, str) or not item.strip():
            raise Namel3ssError(_manifest_error(source_path, f"tags[{idx}] must be a non-empty string"))
        tag = item.strip().lower()
        if tag in seen:
            continue
        seen.add(tag)
        values.append(tag)
    return tuple(values)


def _parse_rating(raw_value: object, *, source_path: Path) -> float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        raise Namel3ssError(_manifest_error(source_path, "rating must be a number when provided"))
    if not isinstance(raw_value, (int, float)):
        raise Namel3ssError(_manifest_error(source_path, "rating must be a number when provided"))
    value = float(raw_value)
    if value < 0 or value > 5:
        raise Namel3ssError(_manifest_error(source_path, "rating must be between 0 and 5"))
    return value


def _resolve_module_path(raw_value: object, *, source_path: Path, plugin_root: Path) -> Path:
    if raw_value is None:
        return (plugin_root / "renderer.py").resolve()
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise Namel3ssError(_manifest_error(source_path, "module must be a non-empty string"))
    return (plugin_root / raw_value).resolve()


def _manifest_error(source_path: Path, detail: str) -> str:
    return f"Invalid UI plugin manifest '{source_path.as_posix()}': {detail}."


__all__ = [
    "ALLOWED_PROP_TYPES",
    "ALLOWED_HOOK_TYPES",
    "CURRENT_EXTENSION_API_VERSION",
    "UIPluginComponentSchema",
    "UIPluginPropSpec",
    "UIPluginSchema",
    "parse_plugin_manifest",
]

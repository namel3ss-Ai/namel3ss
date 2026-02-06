from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


FORMATS_DIR = ".namel3ss"
FORMATS_FILE = "formats.yaml"
SUPPORTED_FORMATS = ("json", "toon")


@dataclass(frozen=True)
class FormatsConfig:
    routes: dict[str, tuple[str, ...]]

    def formats_for_route(self, route_name: str | None) -> tuple[str, ...]:
        if not route_name:
            return ("json",)
        return self.routes.get(route_name, ("json",))


def formats_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / FORMATS_DIR / FORMATS_FILE


def load_formats_config(project_root: str | Path | None, app_path: str | Path | None) -> FormatsConfig:
    path = formats_path(project_root, app_path)
    if path is None or not path.exists():
        return FormatsConfig(routes={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_formats_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_formats_message(path))
    routes_payload = payload.get("routes", payload)
    if not isinstance(routes_payload, dict):
        raise Namel3ssError(_invalid_formats_message(path))
    routes: dict[str, tuple[str, ...]] = {}
    for name, entry in routes_payload.items():
        route_name = str(name).strip()
        if not route_name:
            raise Namel3ssError(_invalid_formats_message(path))
        formats = _parse_format_list(entry, path=path, route_name=route_name)
        routes[route_name] = formats
    return FormatsConfig(routes=routes)


def save_formats_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: FormatsConfig,
) -> Path:
    path = formats_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Formats path could not be resolved.")
    payload: dict[str, object] = {"routes": {}}
    for name in sorted(config.routes.keys()):
        payload["routes"][name] = list(config.routes[name])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _parse_format_list(value: object, *, path: Path, route_name: str) -> tuple[str, ...]:
    if value is None:
        return ("json",)
    if isinstance(value, str):
        formats = [value]
    elif isinstance(value, list):
        formats = [str(item) for item in value]
    elif isinstance(value, dict):
        inner = value.get("formats")
        if isinstance(inner, list):
            formats = [str(item) for item in inner]
        elif isinstance(inner, str):
            formats = [inner]
        else:
            formats = []
    else:
        raise Namel3ssError(_invalid_route_formats_message(path, route_name))
    cleaned = [fmt.strip().lower() for fmt in formats if str(fmt).strip()]
    if not cleaned:
        return ("json",)
    for fmt in cleaned:
        if fmt not in SUPPORTED_FORMATS:
            raise Namel3ssError(_invalid_route_formats_message(path, route_name))
    ordered = []
    for fmt in cleaned:
        if fmt not in ordered:
            ordered.append(fmt)
    return tuple(ordered)


def _invalid_formats_message(path: Path) -> str:
    return build_guidance_message(
        what="Formats config is invalid.",
        why=f"Expected a routes mapping in {path.as_posix()}.",
        fix="Regenerate the file with n3 formats list or edit it to match the expected shape.",
        example="routes:\n  list_users:\n    - json\n    - toon",
    )


def _invalid_route_formats_message(path: Path, route_name: str) -> str:
    return build_guidance_message(
        what=f"Formats for route '{route_name}' are invalid.",
        why=f"Expected json or toon in {path.as_posix()}.",
        fix="List the allowed formats under the route name.",
        example="routes:\n  list_users:\n    - json\n    - toon",
    )


__all__ = [
    "FORMATS_FILE",
    "FORMATS_DIR",
    "SUPPORTED_FORMATS",
    "FormatsConfig",
    "formats_path",
    "load_formats_config",
    "save_formats_config",
]

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


CONVENTIONS_DIR = ".namel3ss"
CONVENTIONS_FILE = "conventions.yaml"
DEFAULT_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE_MAX = 200


@dataclass(frozen=True)
class RouteConventions:
    pagination: bool
    page_size_default: int
    page_size_max: int
    filter_fields: tuple[str, ...]


@dataclass(frozen=True)
class ConventionsConfig:
    routes: dict[str, RouteConventions]
    defaults: RouteConventions

    def for_route(self, route_name: str | None) -> RouteConventions:
        if not route_name:
            return self.defaults
        return self.routes.get(route_name, self.defaults)


def conventions_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / CONVENTIONS_DIR / CONVENTIONS_FILE


def load_conventions_config(project_root: str | Path | None, app_path: str | Path | None) -> ConventionsConfig:
    path = conventions_path(project_root, app_path)
    defaults = RouteConventions(
        pagination=True,
        page_size_default=DEFAULT_PAGE_SIZE,
        page_size_max=DEFAULT_PAGE_SIZE_MAX,
        filter_fields=(),
    )
    if path is None or not path.exists():
        return ConventionsConfig(routes={}, defaults=defaults)
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_conventions_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_conventions_message(path))
    defaults_payload = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    defaults = _parse_route_conventions(defaults_payload, defaults=defaults, path=path)
    routes_payload = payload.get("routes")
    if routes_payload is None:
        routes_payload = {}
    if not isinstance(routes_payload, dict):
        raise Namel3ssError(_invalid_conventions_message(path))
    routes: dict[str, RouteConventions] = {}
    for name, entry in routes_payload.items():
        route_name = str(name).strip()
        if not route_name:
            raise Namel3ssError(_invalid_conventions_message(path))
        if entry is None:
            routes[route_name] = defaults
            continue
        if not isinstance(entry, dict):
            raise Namel3ssError(_invalid_route_conventions_message(path, route_name))
        routes[route_name] = _parse_route_conventions(entry, defaults=defaults, path=path)
    return ConventionsConfig(routes=routes, defaults=defaults)


def save_conventions_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: ConventionsConfig,
) -> Path:
    path = conventions_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Conventions path could not be resolved.")
    payload: dict[str, object] = {
        "defaults": _render_route_conventions(config.defaults),
        "routes": {},
    }
    for name in sorted(config.routes.keys()):
        payload["routes"][name] = _render_route_conventions(config.routes[name])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _parse_route_conventions(
    entry: dict,
    *,
    defaults: RouteConventions,
    path: Path,
) -> RouteConventions:
    pagination = _parse_bool(entry.get("pagination"), default=defaults.pagination, path=path)
    page_size_default = _parse_int(entry.get("page_size_default"), default=defaults.page_size_default, path=path)
    page_size_max = _parse_int(entry.get("page_size_max"), default=defaults.page_size_max, path=path)
    if page_size_default <= 0 or page_size_max <= 0 or page_size_default > page_size_max:
        raise Namel3ssError(_invalid_conventions_message(path))
    filter_fields = _parse_text_list(entry.get("filter_fields"), path=path)
    return RouteConventions(
        pagination=pagination,
        page_size_default=page_size_default,
        page_size_max=page_size_max,
        filter_fields=tuple(sorted(set(filter_fields))),
    )


def _render_route_conventions(conventions: RouteConventions) -> dict[str, object]:
    payload: dict[str, object] = {
        "pagination": conventions.pagination,
        "page_size_default": conventions.page_size_default,
        "page_size_max": conventions.page_size_max,
    }
    if conventions.filter_fields:
        payload["filter_fields"] = list(conventions.filter_fields)
    return payload


def _parse_text_list(value: object, *, path: Path) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    raise Namel3ssError(_invalid_conventions_message(path))


def _parse_bool(value: object, *, default: bool, path: Path) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    raise Namel3ssError(_invalid_conventions_message(path))


def _parse_int(value: object, *, default: int, path: Path) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise Namel3ssError(_invalid_conventions_message(path))


def _invalid_conventions_message(path: Path) -> str:
    return build_guidance_message(
        what="Conventions config is invalid.",
        why=f"Expected defaults and routes in {path.as_posix()}.",
        fix="Regenerate the file with n3 conventions check or edit it to the expected shape.",
        example=(
            "defaults:\n"
            "  pagination: true\n"
            "  page_size_default: 50\n"
            "  page_size_max: 200\n"
            "routes:\n"
            "  list_users:\n"
            "    filter_fields:\n"
            "      - status\n"
            "      - role"
        ),
    )


def _invalid_route_conventions_message(path: Path, route_name: str) -> str:
    return build_guidance_message(
        what=f"Conventions for route '{route_name}' are invalid.",
        why=f"Expected pagination and filter_fields in {path.as_posix()}.",
        fix="Provide pagination flags or filter fields for the route.",
        example=(
            "routes:\n"
            f"  {route_name}:\n"
            "    pagination: false\n"
            "    filter_fields:\n"
            "      - status"
        ),
    )


__all__ = [
    "CONVENTIONS_FILE",
    "CONVENTIONS_DIR",
    "ConventionsConfig",
    "RouteConventions",
    "conventions_path",
    "load_conventions_config",
    "save_conventions_config",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_PAGE_SIZE_MAX",
]

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


PERMISSIONS_DIR = ".namel3ss"
PERMISSIONS_FILE = "permissions.yaml"


@dataclass(frozen=True)
class RouteRequirement:
    roles: tuple[str, ...]
    permissions: tuple[str, ...]

    def requires_auth(self) -> bool:
        return bool(self.roles or self.permissions)


@dataclass(frozen=True)
class RoutePermissions:
    routes: dict[str, RouteRequirement]
    flows: dict[str, RouteRequirement] = field(default_factory=dict)
    secrets: dict[str, RouteRequirement] = field(default_factory=dict)

    def requirement_for(self, route_name: str | None) -> RouteRequirement | None:
        if not route_name:
            return None
        return self.routes.get(route_name)

    def flow_requirement_for(self, flow_name: str | None) -> RouteRequirement | None:
        if not flow_name:
            return None
        return self.flows.get(flow_name)

    def secret_requirement_for(self, secret_name: str | None) -> RouteRequirement | None:
        if not secret_name:
            return None
        return self.secrets.get(secret_name)


def permissions_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return root / PERMISSIONS_DIR / PERMISSIONS_FILE


def load_route_permissions(project_root: str | Path | None, app_path: str | Path | None) -> RoutePermissions:
    path = permissions_path(project_root, app_path)
    if path is None or not path.exists():
        return RoutePermissions(routes={})
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_permissions_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_permissions_message(path))
    route_values: object = payload.get("routes", {})
    flow_values: object = payload.get("flows", {})
    secret_values: object = payload.get("secrets", {})
    has_explicit_sections = any(key in payload for key in ("routes", "flows", "secrets"))
    if not has_explicit_sections:
        route_values = payload
        flow_values = {}
        secret_values = {}
    if route_values is None:
        route_values = {}
    if flow_values is None:
        flow_values = {}
    if secret_values is None:
        secret_values = {}
    if not isinstance(route_values, dict):
        raise Namel3ssError(_invalid_permissions_message(path))
    if not isinstance(flow_values, dict):
        raise Namel3ssError(_invalid_permissions_message(path))
    if not isinstance(secret_values, dict):
        raise Namel3ssError(_invalid_permissions_message(path))
    routes: dict[str, RouteRequirement] = {}
    for route_name, entry in route_values.items():
        name = str(route_name).strip()
        if not name:
            raise Namel3ssError(_invalid_permissions_message(path))
        requirement = _parse_requirement(entry, path, name)
        if requirement is None:
            continue
        routes[name] = requirement
    flows: dict[str, RouteRequirement] = {}
    for flow_name, entry in flow_values.items():
        name = str(flow_name).strip()
        if not name:
            raise Namel3ssError(_invalid_permissions_message(path))
        requirement = _parse_requirement(entry, path, name)
        if requirement is None:
            continue
        flows[name] = requirement
    secrets: dict[str, RouteRequirement] = {}
    for secret_name, entry in secret_values.items():
        name = str(secret_name).strip()
        if not name:
            raise Namel3ssError(_invalid_permissions_message(path))
        requirement = _parse_requirement(entry, path, name)
        if requirement is None:
            continue
        secrets[name] = requirement
    return RoutePermissions(routes=routes, flows=flows, secrets=secrets)


def save_route_permissions(
    project_root: str | Path | None,
    app_path: str | Path | None,
    permissions: RoutePermissions,
) -> Path:
    path = permissions_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Permissions path could not be resolved.")
    payload: dict[str, dict] = {}
    if permissions.routes:
        payload["routes"] = {}
        for name in sorted(permissions.routes.keys()):
            req = permissions.routes[name]
            route_payload: dict[str, object] = {}
            if req.roles:
                route_payload["roles"] = list(req.roles)
            if req.permissions:
                route_payload["permissions"] = list(req.permissions)
            payload["routes"][name] = {"requires": route_payload} if route_payload else {}
    if permissions.flows:
        payload["flows"] = {}
        for name in sorted(permissions.flows.keys()):
            req = permissions.flows[name]
            flow_payload: dict[str, object] = {}
            if req.roles:
                flow_payload["roles"] = list(req.roles)
            if req.permissions:
                flow_payload["permissions"] = list(req.permissions)
            payload["flows"][name] = {"requires": flow_payload} if flow_payload else {}
    if permissions.secrets:
        payload["secrets"] = {}
        for name in sorted(permissions.secrets.keys()):
            req = permissions.secrets[name]
            secret_payload: dict[str, object] = {}
            if req.roles:
                secret_payload["roles"] = list(req.roles)
            if req.permissions:
                secret_payload["permissions"] = list(req.permissions)
            payload["secrets"][name] = {"requires": secret_payload} if secret_payload else {}
    if not payload:
        payload = {"routes": {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def _parse_requirement(entry: object, path: Path, route_name: str) -> RouteRequirement | None:
    if entry is None:
        return None
    if not isinstance(entry, dict):
        raise Namel3ssError(_invalid_route_permissions_message(path, route_name))
    payload = entry.get("requires", entry)
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_route_permissions_message(path, route_name))
    roles = _normalize_text_list(payload.get("roles"))
    permissions = _normalize_text_list(payload.get("permissions"))
    if not roles and not permissions:
        return None
    return RouteRequirement(roles=tuple(sorted(roles)), permissions=tuple(sorted(permissions)))


def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items
    raise Namel3ssError("Permissions must be a list of text values.")


def _invalid_permissions_message(path: Path) -> str:
    return build_guidance_message(
        what="Permissions config is invalid.",
        why=f"Expected a routes mapping in {path.as_posix()}.",
        fix="Regenerate the file with n3 auth require or edit it to match the expected shape.",
        example="routes:\n  get_user:\n    requires:\n      roles:\n        - admin",
    )


def _invalid_route_permissions_message(path: Path, route_name: str) -> str:
    return build_guidance_message(
        what=f"Permissions for route '{route_name}' are invalid.",
        why=f"Expected roles or permissions in {path.as_posix()}.",
        fix="Provide roles or permissions for the route.",
        example="routes:\n  get_user:\n    requires:\n      permissions:\n        - user.read",
    )


__all__ = [
    "RouteRequirement",
    "RoutePermissions",
    "load_route_permissions",
    "save_route_permissions",
    "permissions_path",
]

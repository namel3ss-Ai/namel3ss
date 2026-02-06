from __future__ import annotations

from typing import Callable

from namel3ss.persistence.local_store import LocalStore
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.runtime.auth.route_permissions import load_route_permissions
from namel3ss.runtime.router.definitions import build_definitions, should_persist
from namel3ss.runtime.router.registry import RouteRegistry
from namel3ss.versioning import load_version_config, route_metadata_by_target


def refresh_routes(
    *,
    program,
    registry: RouteRegistry,
    revision: str | None,
    logger: Callable[[str], None] | None = None,
) -> dict[str, list[str]]:
    routes = getattr(program, "routes", []) or []
    permissions = load_route_permissions(getattr(program, "project_root", None), getattr(program, "app_path", None))
    route_version_meta = {}
    if _versioning_quality_mlops_enabled(program):
        version_config = load_version_config(getattr(program, "project_root", None), getattr(program, "app_path", None))
        route_version_meta = route_metadata_by_target(version_config)
    diff = registry.update(
        routes,
        revision=revision,
        requirements=permissions.routes,
        route_version_meta=route_version_meta,
    )
    definitions = build_definitions(program)
    if should_persist(definitions):
        store = LocalStore(getattr(program, "project_root", None), getattr(program, "app_path", None))
        store.save_definitions(definitions)
    if logger and _has_changes(diff):
        added = ", ".join(diff["added"]) if diff["added"] else "none"
        updated = ", ".join(diff["updated"]) if diff["updated"] else "none"
        removed = ", ".join(diff["removed"]) if diff["removed"] else "none"
        logger(f"Routes reloaded. Added: {added}. Updated: {updated}. Removed: {removed}.")
    return diff


def _has_changes(diff: dict[str, list[str]]) -> bool:
    return bool(diff.get("added") or diff.get("updated") or diff.get("removed"))


def _versioning_quality_mlops_enabled(program: object) -> bool:
    raw = getattr(program, "capabilities", ()) or ()
    if not isinstance(raw, (list, tuple)):
        return False
    for item in raw:
        token = normalize_builtin_capability(item if isinstance(item, str) else None)
        if token == "versioning_quality_mlops":
            return True
    return False


__all__ = ["refresh_routes"]

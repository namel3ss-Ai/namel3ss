from __future__ import annotations

from namel3ss.runtime.auth.enforcement import enforce_requirement
from namel3ss.runtime.router.registry import RouteEntry



def enforce_route_permissions(
    entry: RouteEntry,
    *,
    identity: dict | None,
    auth_context: object | None,
) -> None:
    enforce_requirement(entry.requires, resource_name=entry.name, identity=identity, auth_context=auth_context)


__all__ = ["enforce_requirement", "enforce_route_permissions"]

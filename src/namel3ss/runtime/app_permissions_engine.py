from __future__ import annotations

from namel3ss.errors.base import Namel3ssError


KNOWN_APP_PERMISSIONS: tuple[str, ...] = (
    "ai.call",
    "ai.tools",
    "navigation.change_page",
    "ui_state.persistent_write",
    "uploads.read",
    "uploads.write",
)


def normalize_app_permissions(
    raw: object | None,
    *,
    enabled: bool,
) -> dict[str, bool]:
    payload = raw if isinstance(raw, dict) else {}
    if not enabled:
        return {key: True for key in KNOWN_APP_PERMISSIONS}
    return {key: bool(payload.get(key, False)) for key in KNOWN_APP_PERMISSIONS}


def permission_allowed(
    key: str,
    *,
    permissions: dict[str, bool] | None,
    enabled: bool,
) -> bool:
    if key not in KNOWN_APP_PERMISSIONS:
        raise Namel3ssError(f"Unknown application permission '{key}'.")
    if not enabled:
        return True
    if not isinstance(permissions, dict):
        return False
    return bool(permissions.get(key, False))


def require_permission(
    key: str,
    *,
    permissions: dict[str, bool] | None,
    enabled: bool,
    line: int | None = None,
    column: int | None = None,
    reason: str | None = None,
) -> None:
    if permission_allowed(key, permissions=permissions, enabled=enabled):
        return
    domain, action = key.split(".", 1)
    detail = f" for {reason}" if isinstance(reason, str) and reason else ""
    raise Namel3ssError(
        (
            f"Permission denied: {key}{detail}. "
            f"Declare this permission as allowed:\n  {domain}:\n    {action}: allowed"
        ),
        line=line,
        column=column,
    )


__all__ = [
    "KNOWN_APP_PERMISSIONS",
    "normalize_app_permissions",
    "permission_allowed",
    "require_permission",
]

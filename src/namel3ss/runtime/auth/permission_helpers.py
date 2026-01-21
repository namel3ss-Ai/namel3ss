from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.auth.identity_model import _normalize_text_list


def normalize_roles(identity: dict | None) -> list[str]:
    if not isinstance(identity, dict):
        return []
    roles = identity.get("roles")
    if roles is None:
        roles = identity.get("role")
    return _normalize_text_list(roles)


def normalize_permissions(identity: dict | None) -> list[str]:
    if not isinstance(identity, dict):
        return []
    permissions = identity.get("permissions")
    if permissions is None:
        permissions = identity.get("permission")
    if permissions is None:
        permissions = identity.get("scopes")
    if permissions is None:
        permissions = identity.get("scope")
    return _normalize_text_list(permissions)


def has_role(identity: dict | None, role: object) -> bool:
    role_text = _require_text(role, "role")
    return role_text in normalize_roles(identity)


def has_permission(identity: dict | None, permission: object) -> bool:
    perm_text = _require_text(permission, "permission")
    return perm_text in normalize_permissions(identity)


def _require_text(value: object, label: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise Namel3ssError(
        build_guidance_message(
            what=f"{label.capitalize()} must be text.",
            why="Role and permission checks require a text value.",
            fix="Pass a text value.",
            example=f'has_{label}("{label}")',
        )
    )


__all__ = ["has_permission", "has_role", "normalize_permissions", "normalize_roles"]

from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message

ALLOWED_EXTENSION_PERMISSIONS = (
    "net",
    "file:read",
    "file:write",
    "db",
    "ui",
    "tool",
    "memory",
    "memory:read",
    "memory:write",
    "legacy_full_access",
)


def normalize_extension_permission(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token in ALLOWED_EXTENSION_PERMISSIONS:
        return token
    return None


def parse_extension_permissions(
    raw_value: object,
    *,
    source_label: str,
    default_legacy: bool = True,
) -> tuple[str, ...]:
    if raw_value is None:
        return ("legacy_full_access",) if default_legacy else tuple()
    if not isinstance(raw_value, list):
        raise Namel3ssError(_permissions_error(source_label, "permissions must be a list of strings"))
    values: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(raw_value):
        token = normalize_extension_permission(item)
        if token is None:
            raise Namel3ssError(
                _permissions_error(
                    source_label,
                    f"permissions[{idx}]='{item}' is unknown. Allowed: {', '.join(ALLOWED_EXTENSION_PERMISSIONS)}",
                )
            )
        if token in seen:
            continue
        seen.add(token)
        values.append(token)
    if not values and default_legacy:
        return ("legacy_full_access",)
    return tuple(values)


def _permissions_error(source_label: str, detail: str) -> str:
    return build_guidance_message(
        what=f"Invalid extension permissions in {source_label}.",
        why=detail,
        fix="Declare only supported extension permissions.",
        example='permissions:\n  - ui\n  - memory:read',
    )


__all__ = [
    "ALLOWED_EXTENSION_PERMISSIONS",
    "normalize_extension_permission",
    "parse_extension_permissions",
]

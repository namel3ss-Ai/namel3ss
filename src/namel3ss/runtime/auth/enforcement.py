from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.auth.permission_helpers import normalize_permissions, normalize_roles
from namel3ss.runtime.auth.route_permissions import RouteRequirement



def enforce_requirement(
    requirement: RouteRequirement | None,
    *,
    resource_name: str,
    identity: dict | None,
    auth_context: object | None,
) -> None:
    if requirement is None or not requirement.requires_auth():
        return
    authenticated = bool(getattr(auth_context, "authenticated", False)) if auth_context is not None else False
    auth_error = getattr(auth_context, "error", None) if auth_context is not None else None
    if not authenticated:
        raise Namel3ssError(
            _auth_error_message(resource_name, auth_error),
            details={
                "category": "authentication",
                "reason_code": auth_error or "missing_authentication",
                "http_status": _auth_error_status(auth_error),
            },
        )
    roles = normalize_roles(identity)
    permissions = normalize_permissions(identity)
    if requirement.roles and not any(role in roles for role in requirement.roles):
        raise Namel3ssError(
            _permission_denied_message(resource_name),
            details={"category": "permission", "reason_code": "missing_role", "http_status": 403},
        )
    if requirement.permissions and not any(perm in permissions for perm in requirement.permissions):
        raise Namel3ssError(
            _permission_denied_message(resource_name),
            details={"category": "permission", "reason_code": "missing_permission", "http_status": 403},
        )



def _auth_error_status(code: str | None) -> int:
    if code in {"session_revoked", "session_expired"}:
        return 403
    return 401



def _permission_denied_message(resource_name: str) -> str:
    return build_guidance_message(
        what=f'Resource "{resource_name}" access is not permitted.',
        why="The identity does not meet the required role or permission.",
        fix="Provide an identity with the required permissions or update requirements.",
        example="n3 auth require get_user --role admin",
    )



def _auth_error_message(resource_name: str, code: str | None) -> str:
    if code == "token_invalid":
        return build_guidance_message(
            what=f'Resource "{resource_name}" cannot verify the token.',
            why="The bearer token could not be verified.",
            fix="Provide a valid bearer token.",
            example="Authorization: Bearer <token>",
        )
    if code == "token_expired":
        return build_guidance_message(
            what=f'Resource "{resource_name}" requires a valid token.',
            why="The bearer token has expired.",
            fix="Login again to obtain a new token.",
            example="POST /api/login",
        )
    if code == "session_revoked":
        return build_guidance_message(
            what=f'Resource "{resource_name}" requires an active session.',
            why="The session is revoked.",
            fix="Login again to create a new session.",
            example="POST /api/login",
        )
    if code == "session_expired":
        return build_guidance_message(
            what=f'Resource "{resource_name}" requires an active session.',
            why="The session has expired.",
            fix="Login again to create a new session.",
            example="POST /api/login",
        )
    return build_guidance_message(
        what=f'Resource "{resource_name}" requires authentication.',
        why="No active session or token was provided.",
        fix="Login to create a session or provide a bearer token.",
        example="POST /api/login",
    )


__all__ = ["enforce_requirement"]

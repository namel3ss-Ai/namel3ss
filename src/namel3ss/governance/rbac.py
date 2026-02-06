from __future__ import annotations

import base64
import hashlib
import hmac
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.paths import governance_file
from namel3ss.governance.secrets import ensure_master_key, master_key_path
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


ROLES_FILENAME = "roles.yaml"
USERS_FILENAME = "users.yaml"


_DEFAULT_ROLES = {
    "admin": {
        "permissions": [
            "invoke_flow",
            "modify_flow",
            "view_secret",
            "manage_policy",
            "view_audit",
            "manage_auth",
        ]
    },
    "developer": {
        "permissions": ["invoke_flow", "modify_flow", "view_secret", "view_audit"]
    },
    "viewer": {
        "permissions": ["invoke_flow", "view_audit"]
    },
}


def roles_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return governance_file(project_root, app_path, ROLES_FILENAME)



def users_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return governance_file(project_root, app_path, USERS_FILENAME)



def list_users(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    users = _load_users_map(project_root, app_path)
    rows: list[dict[str, object]] = []
    for username in sorted(users.keys()):
        entry = users[username]
        roles = sorted(set(_normalize_text_list(entry.get("roles"))))
        token = str(entry.get("token") or "")
        rows.append(
            {
                "username": username,
                "roles": roles,
                "token": token,
                "tenant": _normalize_tenant_id(entry.get("tenant")),
                "permissions": sorted(set(_permissions_for_roles(roles, project_root, app_path))),
            }
        )
    return rows



def add_user(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    username: str,
    roles: list[str] | None = None,
    token: str | None = None,
    tenant: str | None = None,
) -> tuple[Path, dict[str, object]]:
    normalized_user = _normalize_username(username)
    if not normalized_user:
        raise Namel3ssError(_invalid_username_message())

    existing_roles = _load_roles_map(project_root, app_path, ensure_defaults=True)
    assigned_roles = sorted(set(_normalize_role_names(roles or ["viewer"])))
    missing_roles = [role for role in assigned_roles if role not in existing_roles]
    if missing_roles:
        raise Namel3ssError(_unknown_roles_message(missing_roles))

    path = users_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Users path could not be resolved.")
    users = _load_users_map(project_root, app_path)
    if token is None:
        token = generate_token(normalized_user)
    users[normalized_user] = {
        "roles": assigned_roles,
        "token": token,
        "tenant": _normalize_tenant_id(tenant),
    }
    _write_users_map(path, users)
    return path, {
        "username": normalized_user,
        "roles": assigned_roles,
        "token": token,
        "tenant": _normalize_tenant_id(tenant),
    }



def assign_role(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    username: str,
    role: str,
) -> tuple[Path, dict[str, object]]:
    normalized_user = _normalize_username(username)
    role_name = _normalize_role_name(role)
    if not normalized_user:
        raise Namel3ssError(_invalid_username_message())
    if not role_name:
        raise Namel3ssError(_invalid_role_message())

    roles = _load_roles_map(project_root, app_path, ensure_defaults=True)
    if role_name not in roles:
        raise Namel3ssError(_unknown_roles_message([role_name]))

    path = users_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Users path could not be resolved.")
    users = _load_users_map(project_root, app_path)
    current = users.get(normalized_user)
    if current is None:
        raise Namel3ssError(_missing_user_message(normalized_user))
    existing = sorted(set(_normalize_text_list(current.get("roles"))))
    if role_name not in existing:
        existing.append(role_name)
        existing = sorted(set(existing))
    users[normalized_user] = {
        "roles": existing,
        "token": str(current.get("token") or generate_token(normalized_user)),
        "tenant": _normalize_tenant_id(current.get("tenant")),
    }
    _write_users_map(path, users)
    return path, {
        "username": normalized_user,
        "roles": existing,
        "token": str(users[normalized_user].get("token") or ""),
        "tenant": _normalize_tenant_id(users[normalized_user].get("tenant")),
    }



def resolve_identity_from_token(
    token: str,
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> dict[str, object] | None:
    clean = str(token or "").strip()
    if not clean:
        return None
    try:
        users = _load_users_map(project_root, app_path)
    except Namel3ssError:
        return None
    for username in sorted(users.keys()):
        entry = users[username]
        stored = str(entry.get("token") or "")
        if stored != clean:
            continue
        roles = sorted(set(_normalize_text_list(entry.get("roles"))))
        permissions = sorted(set(_permissions_for_roles(roles, project_root, app_path)))
        identity = {
            "subject": username,
            "username": username,
            "roles": roles,
            "permissions": permissions,
        }
        tenant = _normalize_tenant_id(entry.get("tenant"))
        if tenant:
            identity["tenant"] = tenant
            identity["tenant_id"] = tenant
            identity["tenants"] = [tenant]
        return identity
    return None



def generate_token(username: str) -> str:
    normalized = _normalize_username(username)
    if not normalized:
        raise Namel3ssError(_invalid_username_message())
    key = _load_master_key_bytes()
    digest = hmac.new(key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    return f"{normalized}_{digest}"



def _load_roles_map(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    ensure_defaults: bool,
) -> dict[str, dict[str, object]]:
    path = roles_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Roles path could not be resolved.")
    if not path.exists():
        if ensure_defaults:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"roles": _DEFAULT_ROLES}
            path.write_text(render_yaml(payload), encoding="utf-8")
            return {name: dict(data) for name, data in _DEFAULT_ROLES.items()}
        return {}
    try:
        parsed = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_yaml_message(path)) from err
    if not isinstance(parsed, dict):
        raise Namel3ssError(_invalid_yaml_message(path))
    raw_roles = parsed.get("roles")
    if raw_roles is None:
        raw_roles = parsed
    if not isinstance(raw_roles, dict):
        raise Namel3ssError(_invalid_yaml_message(path))
    roles: dict[str, dict[str, object]] = {}
    for key in sorted(raw_roles.keys(), key=lambda item: str(item)):
        role_name = _normalize_role_name(str(key))
        if not role_name:
            continue
        value = raw_roles[key]
        if isinstance(value, dict):
            perms = sorted(set(_normalize_text_list(value.get("permissions"))))
        elif isinstance(value, list):
            perms = sorted(set(_normalize_text_list(value)))
        else:
            perms = []
        roles[role_name] = {"permissions": perms}
    return roles



def _load_users_map(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, dict[str, object]]:
    path = users_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Users path could not be resolved.")
    if not path.exists():
        return {}
    try:
        parsed = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_yaml_message(path)) from err
    if not isinstance(parsed, dict):
        raise Namel3ssError(_invalid_yaml_message(path))
    raw_users = parsed.get("users")
    if raw_users is None:
        raw_users = parsed
    if not isinstance(raw_users, dict):
        raise Namel3ssError(_invalid_yaml_message(path))
    users: dict[str, dict[str, object]] = {}
    for key in sorted(raw_users.keys(), key=lambda item: str(item)):
        username = _normalize_username(str(key))
        if not username:
            continue
        value = raw_users[key]
        if not isinstance(value, dict):
            continue
        roles = sorted(set(_normalize_text_list(value.get("roles"))))
        token = str(value.get("token") or "")
        tenant = _normalize_tenant_id(value.get("tenant"))
        users[username] = {
            "roles": roles,
            "token": token,
            "tenant": tenant,
        }
    return users



def _write_users_map(path: Path, users: dict[str, dict[str, object]]) -> None:
    payload = {
        "users": {
            username: {
                "roles": sorted(set(_normalize_text_list(entry.get("roles")))),
                "token": str(entry.get("token") or ""),
                **({"tenant": _normalize_tenant_id(entry.get("tenant"))} if _normalize_tenant_id(entry.get("tenant")) else {}),
            }
            for username, entry in sorted(users.items(), key=lambda item: item[0])
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")



def _permissions_for_roles(
    roles: list[str],
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> list[str]:
    role_map = _load_roles_map(project_root, app_path, ensure_defaults=True)
    permissions: list[str] = []
    for role in sorted(set(roles)):
        entry = role_map.get(role)
        if not isinstance(entry, dict):
            continue
        for permission in _normalize_text_list(entry.get("permissions")):
            if permission not in permissions:
                permissions.append(permission)
    return permissions



def _normalize_username(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    cleaned: list[str] = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-", "."}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    text = "".join(cleaned).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text



def _normalize_role_name(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    cleaned: list[str] = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    text = "".join(cleaned).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text


def _normalize_tenant_id(value: object) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    cleaned: list[str] = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    text = "".join(cleaned).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text



def _normalize_role_names(values: list[str]) -> list[str]:
    return [_normalize_role_name(value) for value in values if _normalize_role_name(value)]



def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        iterable = sorted(value, key=lambda item: str(item)) if isinstance(value, set) else list(value)
        for item in iterable:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []



def _load_master_key_bytes() -> bytes:
    path = ensure_master_key()
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise Namel3ssError(_invalid_master_key_message(path))
    try:
        padded = raw + "=" * ((4 - len(raw) % 4) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        try:
            decoded = bytes.fromhex(raw)
        except Exception as err:
            raise Namel3ssError(_invalid_master_key_message(path)) from err
    if not decoded:
        raise Namel3ssError(_invalid_master_key_message(path))
    return hashlib.sha256(decoded).digest()



def _invalid_yaml_message(path: Path) -> str:
    return build_guidance_message(
        what="RBAC config is invalid.",
        why=f"Could not parse {path.as_posix()}.",
        fix="Fix YAML syntax and key shapes.",
        example="users:\n  alice:\n    roles:\n      - developer",
    )



def _invalid_username_message() -> str:
    return build_guidance_message(
        what="Username is invalid.",
        why="Username cannot be empty.",
        fix="Use letters, numbers, dash, underscore, or dot.",
        example="n3 auth add-user alice",
    )



def _invalid_role_message() -> str:
    return build_guidance_message(
        what="Role name is invalid.",
        why="Role name cannot be empty.",
        fix="Provide a role name.",
        example="n3 auth assign-role alice developer",
    )



def _unknown_roles_message(roles: list[str]) -> str:
    items = ", ".join(sorted(roles))
    return build_guidance_message(
        what="Role is not defined.",
        why=f"Missing roles: {items}.",
        fix="Define roles in .namel3ss/roles.yaml before assigning them.",
        example="roles:\n  developer:\n    permissions:\n      - invoke_flow",
    )



def _missing_user_message(username: str) -> str:
    return build_guidance_message(
        what=f"User '{username}' was not found.",
        why="assign-role needs an existing user.",
        fix="Create the user first with n3 auth add-user.",
        example=f"n3 auth add-user {username}",
    )



def _invalid_master_key_message(path: Path) -> str:
    return build_guidance_message(
        what="Master key is invalid.",
        why=f"Could not decode {path.as_posix()}.",
        fix="Write a base64 or hex key value.",
        example=master_key_path().as_posix(),
    )


__all__ = [
    "ROLES_FILENAME",
    "USERS_FILENAME",
    "add_user",
    "assign_role",
    "generate_token",
    "list_users",
    "resolve_identity_from_token",
    "roles_path",
    "users_path",
]

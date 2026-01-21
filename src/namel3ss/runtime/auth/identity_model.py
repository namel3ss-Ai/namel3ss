from __future__ import annotations

from typing import Iterable


_SUBJECT_KEYS = ("subject", "id", "user_id", "email", "name")


def normalize_identity(identity: dict | None) -> dict:
    if not isinstance(identity, dict):
        return {}
    data = dict(identity)
    subject = _resolve_subject(data)
    if subject is not None:
        data["subject"] = subject
    roles = _normalize_text_list(data.get("roles"))
    role_value = data.get("role")
    if not roles and role_value is not None:
        roles = _normalize_text_list(role_value)
    if roles:
        data["roles"] = roles
        if "role" not in data:
            data["role"] = roles[0]
    permissions = _normalize_text_list(data.get("permissions"))
    if not permissions:
        permissions = _normalize_text_list(data.get("permission"))
    if not permissions:
        permissions = _normalize_text_list(data.get("scopes"))
    if not permissions:
        permissions = _normalize_text_list(data.get("scope"))
    if permissions:
        data["permissions"] = permissions
    return data


def build_identity_summary(identity: dict | None) -> dict:
    normalized = normalize_identity(identity)
    summary = {
        "subject": normalized.get("subject"),
        "roles": list(normalized.get("roles") or []),
        "permissions": list(normalized.get("permissions") or []),
        "trust_level": normalized.get("trust_level"),
    }
    return summary


def _resolve_subject(identity: dict) -> str | None:
    for key in _SUBJECT_KEYS:
        value = identity.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    items: Iterable[object]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if "," in raw:
            items = [item.strip() for item in raw.split(",")]
        else:
            items = [raw]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    elif isinstance(value, set):
        items = sorted(value, key=lambda item: str(item))
    else:
        items = [value]
    normalized: list[str] = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        if text not in normalized:
            normalized.append(text)
    return normalized


__all__ = ["build_identity_summary", "normalize_identity"]

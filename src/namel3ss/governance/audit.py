from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.governance.paths import governance_file


AUDIT_FILENAME = "audit.jsonl"
_REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "secret",
    "token",
    "password",
    "key",
    "credential",
    "authorization",
)


def audit_log_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return governance_file(project_root, app_path, AUDIT_FILENAME)


def list_audit_entries(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    user: str | None = None,
    action: str | None = None,
) -> list[dict[str, object]]:
    path = audit_log_path(project_root, app_path)
    if path is None or not path.exists():
        return []
    selected_user = (user or "").strip()
    selected_action = (action or "").strip()
    entries: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        if selected_user and str(parsed.get("user") or "") != selected_user:
            continue
        if selected_action and str(parsed.get("action") or "") != selected_action:
            continue
        entries.append(_normalize_entry(parsed))
    entries.sort(key=lambda item: int(item.get("timestamp") or 0))
    return entries


def record_audit_entry(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    user: str,
    action: str,
    resource: str,
    status: str,
    details: dict[str, object] | None = None,
) -> dict[str, object] | None:
    path = audit_log_path(project_root, app_path)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _next_timestamp(path),
        "user": _safe_text(user, default="anonymous"),
        "action": _safe_text(action, default="unknown_action"),
        "resource": _safe_text(resource, default="unknown_resource"),
        "status": _safe_text(status, default="unknown"),
        "details": _sanitize_payload(details or {}),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(entry, pretty=False, drop_run_keys=False) + "\n")
    return entry


def _next_timestamp(path: Path) -> int:
    if not path.exists():
        return 1
    last_timestamp = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        value = parsed.get("timestamp")
        if isinstance(value, int):
            if value > last_timestamp:
                last_timestamp = value
        elif isinstance(value, str) and value.isdigit():
            number = int(value)
            if number > last_timestamp:
                last_timestamp = number
    return last_timestamp + 1


def _normalize_entry(entry: dict[str, object]) -> dict[str, object]:
    details = entry.get("details")
    normalized = {
        "timestamp": _coerce_int(entry.get("timestamp")),
        "user": _safe_text(entry.get("user"), default="anonymous"),
        "action": _safe_text(entry.get("action"), default="unknown_action"),
        "resource": _safe_text(entry.get("resource"), default="unknown_resource"),
        "status": _safe_text(entry.get("status"), default="unknown"),
        "details": _sanitize_payload(details if isinstance(details, dict) else {}),
    }
    return normalized


def _coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _safe_text(value: object, *, default: str) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return default


def _sanitize_payload(value: object) -> object:
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_text = str(key)
            child = value[key]
            if _is_sensitive_key(key_text):
                cleaned[key_text] = _REDACTED
            else:
                cleaned[key_text] = _sanitize_payload(child)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, set):
        return [_sanitize_payload(item) for item in sorted(value, key=lambda item: str(item))]
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def resolve_actor(
    identity: dict | None,
    auth_context: object | None = None,
    *,
    fallback: str = "anonymous",
) -> str:
    if isinstance(identity, dict):
        for key in ("subject", "username", "email", "id", "name"):
            value = identity.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    auth_identity = getattr(auth_context, "identity", None)
    if isinstance(auth_identity, dict):
        for key in ("subject", "username", "email", "id", "name"):
            value = auth_identity.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback


def summarize_status(entries: Iterable[dict[str, object]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for entry in entries:
        status = _safe_text(entry.get("status"), default="unknown")
        summary[status] = int(summary.get(status, 0)) + 1
    return {key: summary[key] for key in sorted(summary.keys())}


__all__ = [
    "AUDIT_FILENAME",
    "audit_log_path",
    "list_audit_entries",
    "record_audit_entry",
    "resolve_actor",
    "summarize_status",
]

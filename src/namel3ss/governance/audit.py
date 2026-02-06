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
    policy = _load_retention_policy(project_root, app_path)
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
        entries.append(_normalize_entry(parsed, extra_redact=policy.anonymize_fields))
    entries.sort(key=lambda item: int(item.get("timestamp") or 0))
    entries, changed = _apply_retention_policy(entries, policy)
    if changed:
        _rewrite_entries(path, entries)
    filtered: list[dict[str, object]] = []
    for parsed in entries:
        if selected_user and str(parsed.get("user") or "") != selected_user:
            continue
        if selected_action and str(parsed.get("action") or "") != selected_action:
            continue
        filtered.append(parsed)
    return filtered


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
    policy = _load_retention_policy(project_root, app_path)
    entry = {
        "timestamp": _next_timestamp(path),
        "user": _safe_text(user, default="anonymous"),
        "action": _safe_text(action, default="unknown_action"),
        "resource": _safe_text(resource, default="unknown_resource"),
        "status": _safe_text(status, default="unknown"),
        "details": _sanitize_payload(details or {}, extra_redact=policy.anonymize_fields),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(entry, pretty=False, drop_run_keys=False) + "\n")
    if policy.enabled:
        entries = list_audit_entries(project_root, app_path)
        if entries:
            newest = entries[-1]
            if isinstance(newest, dict):
                return newest
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


def _normalize_entry(entry: dict[str, object], *, extra_redact: set[str] | None = None) -> dict[str, object]:
    details = entry.get("details")
    normalized = {
        "timestamp": _coerce_int(entry.get("timestamp")),
        "user": _safe_text(entry.get("user"), default="anonymous"),
        "action": _safe_text(entry.get("action"), default="unknown_action"),
        "resource": _safe_text(entry.get("resource"), default="unknown_resource"),
        "status": _safe_text(entry.get("status"), default="unknown"),
        "details": _sanitize_payload(details if isinstance(details, dict) else {}, extra_redact=extra_redact),
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


def _sanitize_payload(value: object, *, extra_redact: set[str] | None = None) -> object:
    extra = extra_redact or set()
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_text = str(key)
            child = value[key]
            if _is_sensitive_key(key_text, extra_redact=extra):
                cleaned[key_text] = _REDACTED
            else:
                cleaned[key_text] = _sanitize_payload(child, extra_redact=extra)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_payload(item, extra_redact=extra) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_payload(item, extra_redact=extra) for item in value]
    if isinstance(value, set):
        return [_sanitize_payload(item, extra_redact=extra) for item in sorted(value, key=lambda item: str(item))]
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def _is_sensitive_key(key: str, *, extra_redact: set[str] | None = None) -> bool:
    lowered = key.lower()
    if extra_redact and lowered in extra_redact:
        return True
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


class _RetentionPolicy:
    def __init__(self, *, enabled: bool, audit_retention_days: int, anonymize_fields: set[str]) -> None:
        self.enabled = enabled
        self.audit_retention_days = int(audit_retention_days)
        self.anonymize_fields = set(anonymize_fields)


def _load_retention_policy(project_root: str | Path | None, app_path: str | Path | None) -> _RetentionPolicy:
    try:
        from namel3ss.config.security_compliance import load_retention_config

        config = load_retention_config(project_root, app_path, required=False)
    except Exception:
        config = None
    if config is None:
        return _RetentionPolicy(enabled=False, audit_retention_days=0, anonymize_fields=set())
    anonymize_fields: set[str] = set()
    for rule in config.records.values():
        for field in rule.anonymize_fields:
            normalized = str(field).strip().lower()
            if normalized:
                anonymize_fields.add(normalized)
    return _RetentionPolicy(
        enabled=bool(config.audit_enabled),
        audit_retention_days=max(0, int(config.audit_retention_days)),
        anonymize_fields=anonymize_fields,
    )


def _apply_retention_policy(
    entries: list[dict[str, object]],
    policy: _RetentionPolicy,
) -> tuple[list[dict[str, object]], bool]:
    if not entries:
        return entries, False
    changed = False
    if policy.audit_retention_days > 0:
        latest = max(int(item.get("timestamp") or 0) for item in entries)
        cutoff = max(0, latest - policy.audit_retention_days + 1)
        kept = [entry for entry in entries if int(entry.get("timestamp") or 0) >= cutoff]
        if len(kept) != len(entries):
            entries = kept
            changed = True
    if policy.anonymize_fields:
        redacted: list[dict[str, object]] = []
        for entry in entries:
            details = entry.get("details")
            sanitized = _sanitize_payload(details if isinstance(details, dict) else {}, extra_redact=policy.anonymize_fields)
            if sanitized != details:
                changed = True
            next_entry = dict(entry)
            next_entry["details"] = sanitized
            redacted.append(next_entry)
        entries = redacted
    return entries, changed


def _rewrite_entries(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [canonical_json_dumps(entry, pretty=False, drop_run_keys=False) for entry in entries]
    text = ("\n".join(lines) + ("\n" if lines else ""))
    path.write_text(text, encoding="utf-8")


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

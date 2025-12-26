from __future__ import annotations

from pathlib import Path

from namel3ss.cli.observe_mode import _parse_duration
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.module_loader import load_project
from namel3ss.runtime.audit.recorder import audit_schema, redact_payload as redact_audit
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.secrets import collect_secret_values, redact_payload


def get_data_summary_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    project = load_project(app_file)
    config = load_config(app_path=app_file, root=project_root)
    promotion = load_state(project_root)
    active = promotion.get("active") or {}
    target = active.get("target") or parse_target(None).name
    identity_mode, identity_defaults = _identity_mode(project, config)
    tenant_info = _tenant_info(project, config)
    return {
        "schema_version": 1,
        "engine_target": target,
        "persistence": _persistence_summary(config),
        "identity": {
            "mode": identity_mode,
            "defaults": identity_defaults,
        },
        "tenant": tenant_info,
    }


def get_audit_payload(
    app_path: str,
    *,
    since: str | None,
    limit: int,
    filter_text: str | None,
) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    config = load_config(app_path=app_file, root=project_root)
    store = resolve_store(config=config)
    schema = audit_schema()
    try:
        records = store.list_records(schema, limit=max(limit, 0) or 200)
    except Namel3ssError as err:
        return {"schema_version": 1, "status": "error", "error": str(err), "events": []}
    filtered = _filter_audit(records, since, filter_text)
    if limit > 0:
        filtered = filtered[:limit]
    secrets = collect_secret_values(config)
    redacted = [redact_payload(redact_audit(entry), secrets) for entry in filtered]
    return {"schema_version": 1, "events": redacted}


def _persistence_summary(config) -> dict:
    target = (config.persistence.target or "memory").lower()
    descriptor = None
    if target == "sqlite":
        descriptor = config.persistence.db_path
    elif target == "postgres":
        descriptor = "postgres (url set)" if config.persistence.database_url else "postgres (missing url)"
    elif target == "edge":
        descriptor = "edge (url set)" if config.persistence.edge_kv_url else "edge (missing url)"
    elif target == "memory":
        descriptor = "memory"
    return {"target": target, "descriptor": descriptor}


def _identity_mode(project, config) -> tuple[str, list[str]]:
    has_schema = getattr(project.program, "identity", None) is not None
    defaults = sorted(config.identity.defaults.keys())
    if not has_schema:
        return "none", defaults
    if defaults:
        return "dev_defaults", defaults
    return "runtime_required", defaults


def _tenant_info(project, config) -> dict:
    records = getattr(project.program, "records", [])
    tenant_paths = [rec.tenant_key for rec in records if getattr(rec, "tenant_key", None)]
    enabled = bool(tenant_paths)
    current = None
    if enabled and config.identity.defaults:
        for path in tenant_paths:
            if not path:
                continue
            value = _lookup_path(config.identity.defaults, path)
            if value:
                current = value
                break
    return {
        "enabled": enabled,
        "keys": [".".join(path) for path in tenant_paths if path],
        "current": current,
    }


def _lookup_path(identity: dict, path: list[str]) -> str | None:
    current: object = identity
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current.get(part)
    return str(current) if isinstance(current, str) else None


def _filter_audit(records: list[dict], since: str | None, filter_text: str | None) -> list[dict]:
    since_seconds = _parse_duration(since) if since else None
    if since_seconds:
        threshold = _timestamp_now() - since_seconds
        records = [rec for rec in records if _as_float(rec.get("timestamp")) >= threshold]
    mode = None
    if filter_text:
        raw = filter_text.strip()
        if ":" in raw:
            prefix, rest = raw.split(":", 1)
            prefix = prefix.lower().strip()
            if prefix in {"flow", "action"}:
                mode = prefix
                filter_text = rest
    if filter_text:
        needle = filter_text.lower().strip()
        if needle:
            records = [rec for rec in records if _matches_filter(rec, needle, mode)]
    records = sorted(records, key=lambda rec: _as_float(rec.get("timestamp")), reverse=True)
    return records


def _matches_filter(entry: dict, needle: str, mode: str | None) -> bool:
    flow = str(entry.get("flow") or "").lower()
    action = str(entry.get("action") or "").lower()
    if mode == "flow":
        return needle in flow
    if mode == "action":
        return needle in action
    haystack = " ".join([flow, action]).lower()
    return needle in haystack


def _as_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _timestamp_now() -> float:
    import time

    return time.time()


__all__ = ["get_audit_payload", "get_data_summary_payload"]

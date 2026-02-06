from __future__ import annotations

import json
import time
from pathlib import Path

from namel3ss.config.security_compliance import load_retention_config
from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.feedback.store import feedback_path
from namel3ss.governance.audit import audit_log_path
from namel3ss.governance.secrets import vault_path
from namel3ss.mlops.client import mlops_cache_path, mlops_snapshot_path
from namel3ss.observability.trace_runs import TRACE_INDEX_FILENAME, trace_runs_root
from namel3ss.retrain.jobs import retrain_jobs_path
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml


_REDACTED = "[REDACTED]"
_SECURITY_CONFIG_FILENAME = "security.yaml"


def enforce_retention_policies(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    now_epoch_seconds: float | None = None,
) -> dict[str, object]:
    now_epoch = float(now_epoch_seconds if now_epoch_seconds is not None else time.time())
    rules = _load_retention_rules(project_root, app_path)
    anonymize_fields = _load_anonymize_fields(project_root, app_path)
    removed: list[str] = []
    redacted: list[str] = []

    removed.extend(_purge_trace_runs(project_root, app_path, days=rules.get("traces"), now_epoch=now_epoch))
    removed.extend(_purge_file(feedback_path(project_root, app_path, allow_create=False), days=rules.get("feedback"), now_epoch=now_epoch))
    removed.extend(_purge_file(retrain_jobs_path(project_root, app_path, allow_create=False), days=rules.get("retrain"), now_epoch=now_epoch))
    removed.extend(_purge_file(mlops_cache_path(project_root, app_path), days=rules.get("models"), now_epoch=now_epoch))
    removed.extend(_purge_file(mlops_snapshot_path(project_root, app_path), days=rules.get("models"), now_epoch=now_epoch))
    removed.extend(_purge_file(vault_path(project_root, app_path), days=rules.get("secrets"), now_epoch=now_epoch))
    removed.extend(_purge_file(audit_log_path(project_root, app_path), days=rules.get("audit"), now_epoch=now_epoch))
    removed.extend(_purge_persist_datasets(project_root, app_path, days=rules.get("datasets"), now_epoch=now_epoch))

    if anonymize_fields:
        redacted.extend(_redact_jsonl_file(feedback_path(project_root, app_path, allow_create=False), anonymize_fields))
        redacted.extend(_redact_jsonl_file(audit_log_path(project_root, app_path), anonymize_fields))
        redacted.extend(_redact_persist_datasets(project_root, app_path, anonymize_fields))

    return {
        "ok": True,
        "retention_rules": {key: rules[key] for key in sorted(rules.keys())},
        "removed_count": len(removed),
        "redacted_count": len(redacted),
        "removed": sorted(removed),
        "redacted": sorted(redacted),
    }


def _load_retention_rules(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, int]:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return {}
    path = Path(root) / _SECURITY_CONFIG_FILENAME
    if not path.exists():
        return {}
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_security_config_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_security_config_message(path, "top-level value must be a map"))
    raw = payload.get("retention")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise Namel3ssError(_invalid_security_config_message(path, "retention must be a map of data_type:days"))
    rules: dict[str, int] = {}
    for key in sorted(raw.keys(), key=lambda item: str(item)):
        name = str(key or "").strip().lower()
        if not name:
            continue
        value = raw.get(key)
        try:
            days = int(value)
        except Exception as err:
            raise Namel3ssError(_invalid_retention_days_message(name, value)) from err
        if days < 1:
            raise Namel3ssError(_invalid_retention_days_message(name, value))
        rules[name] = days
    return rules


def _load_anonymize_fields(project_root: str | Path | None, app_path: str | Path | None) -> set[str]:
    config = load_retention_config(project_root, app_path, required=False)
    if config is None:
        return set()
    fields: set[str] = set()
    for rule in config.records.values():
        for field in rule.anonymize_fields:
            text = str(field or "").strip().lower()
            if text:
                fields.add(text)
    return fields


def _purge_trace_runs(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    days: int | None,
    now_epoch: float,
) -> list[str]:
    root = trace_runs_root(project_root, app_path, allow_create=False)
    if root is None or not root.exists():
        return []
    removed: list[str] = []
    for path in sorted(root.glob("*.jsonl"), key=lambda item: item.name):
        removed.extend(_purge_file(path, days=days, now_epoch=now_epoch))
    index_path = root / TRACE_INDEX_FILENAME
    if index_path.exists():
        _repair_trace_index(root, index_path)
    return removed


def _repair_trace_index(root: Path, index_path: Path) -> None:
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(payload, dict):
        return
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return
    existing_ids = {path.stem for path in root.glob("*.jsonl")}
    filtered = [row for row in runs if isinstance(row, dict) and str(row.get("run_id") or "") in existing_ids]
    filtered.sort(key=lambda row: int(row.get("sequence") or 0))
    latest_run_id = ""
    next_counter = 1
    if filtered:
        latest_run_id = str(filtered[-1].get("run_id") or "")
        next_counter = max(int(row.get("sequence") or 0) for row in filtered) + 1
    payload["runs"] = filtered
    payload["latest_run_id"] = latest_run_id or None
    payload["next_counter"] = max(1, int(next_counter))
    canonical_json_dump(index_path, payload, pretty=True, drop_run_keys=False)


def _purge_persist_datasets(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    days: int | None,
    now_epoch: float,
) -> list[str]:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return []
    removed: list[str] = []
    uploads_root = Path(root) / ".namel3ss" / "uploads"
    persist_root = Path(root) / ".namel3ss" / "persist"
    if uploads_root.exists():
        for path in sorted(uploads_root.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_file():
                removed.extend(_purge_file(path, days=days, now_epoch=now_epoch))
    if persist_root.exists():
        for path in sorted(persist_root.rglob("datasets.json"), key=lambda item: item.as_posix()):
            removed.extend(_purge_file(path, days=days, now_epoch=now_epoch))
    return removed


def _purge_file(path: Path | None, *, days: int | None, now_epoch: float) -> list[str]:
    if path is None or days is None:
        return []
    if not path.exists():
        return []
    age_seconds = max(0.0, now_epoch - float(path.stat().st_mtime))
    max_age = float(days) * 86400.0
    if age_seconds <= max_age:
        return []
    path.unlink(missing_ok=True)
    return [path.as_posix()]


def _redact_jsonl_file(path: Path | None, fields: set[str]) -> list[str]:
    if path is None or not path.exists() or not fields:
        return []
    rows: list[dict[str, object]] = []
    changed = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        redacted = _redact_value(payload, fields)
        if redacted != payload:
            changed = True
        rows.append(redacted)
    if not changed:
        return []
    text = "\n".join(canonical_json_dumps(row, pretty=False, drop_run_keys=False) for row in rows)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    return [path.as_posix()]


def _redact_persist_datasets(project_root: str | Path | None, app_path: str | Path | None, fields: set[str]) -> list[str]:
    if not fields:
        return []
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return []
    changed_paths: list[str] = []
    persist_root = Path(root) / ".namel3ss" / "persist"
    if not persist_root.exists():
        return []
    for path in sorted(persist_root.rglob("datasets.json"), key=lambda item: item.as_posix()):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        redacted = _redact_value(payload, fields)
        if redacted == payload:
            continue
        canonical_json_dump(path, redacted, pretty=True, drop_run_keys=False)
        changed_paths.append(path.as_posix())
    return changed_paths


def _redact_value(value: object, fields: set[str]) -> object:
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            key_text = str(key)
            if key_text.lower() in fields:
                out[key_text] = _REDACTED
            else:
                out[key_text] = _redact_value(value[key], fields)
        return out
    if isinstance(value, list):
        return [_redact_value(item, fields) for item in value]
    return value


def _invalid_security_config_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="security.yaml retention config is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Set retention as a map of data_type to positive day count.",
        example="retention:\n  traces: 30\n  datasets: 90",
    )


def _invalid_retention_days_message(name: str, value: object) -> str:
    return build_guidance_message(
        what=f"Retention value for '{name}' is invalid.",
        why=f"Expected a positive integer day count, got '{value}'.",
        fix="Set retention values to integers greater than zero.",
        example="retention:\n  traces: 30",
    )


__all__ = ["enforce_retention_policies"]


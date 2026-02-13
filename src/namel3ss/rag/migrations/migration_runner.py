from __future__ import annotations

from copy import deepcopy

from namel3ss.rag.contracts.value_norms import int_value, map_value, merge_extensions, text_value
from namel3ss.rag.determinism.json_policy import canonical_contract_hash
from namel3ss.rag.migrations.migration_apply import (
    already_applied_step_result,
    apply_migration_step,
    build_step_summary,
    normalize_step_result_rows,
)
from namel3ss.rag.migrations.migration_contract import (
    MIGRATION_MANIFEST_SCHEMA_VERSION,
    build_migration_manifest,
    build_migration_step,
    normalize_migration_manifest,
    normalize_migration_step,
)


MIGRATION_STATE_SCHEMA_VERSION = "rag.migration_state@1"
MIGRATION_REPORT_SCHEMA_VERSION = "rag.migration_report@1"


def ensure_migration_state(state: dict) -> dict[str, object]:
    existing = state.get("rag_migrations")
    data = map_value(existing)
    normalized = {
        "schema_version": text_value(data.get("schema_version"), default=MIGRATION_STATE_SCHEMA_VERSION)
        or MIGRATION_STATE_SCHEMA_VERSION,
        "applied_manifests": _normalize_applied_manifests(data.get("applied_manifests")),
        "applied_steps": _normalize_applied_steps(data.get("applied_steps")),
    }
    state["rag_migrations"] = normalized
    return normalized


def run_migration_manifest(
    *,
    state: dict,
    manifest: object,
    dry_run: bool = False,
    schema_version: str = MIGRATION_REPORT_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest_value = normalize_migration_manifest(manifest)
    working_state = deepcopy(state)
    migration_state = ensure_migration_state(working_state)
    manifest_id = text_value(manifest_value.get("manifest_id"))
    already_applied = manifest_id in dict(migration_state.get("applied_manifests") or {})
    state_hash_before = canonical_contract_hash(working_state)
    step_rows = list(manifest_value.get("steps") or [])

    if already_applied and not dry_run:
        step_results = [already_applied_step_result(step) for step in step_rows]
        state_hash_after = state_hash_before
        state_hash_replay = state_hash_after
        replay_safe = True
        status = "already_applied"
    else:
        step_results = [apply_migration_step(working_state, step) for step in step_rows]
        failed = any(text_value(row.get("status")) == "failed" for row in step_results)
        summary = build_step_summary(step_results)
        if failed:
            status = "failed"
        elif summary["applied_steps"] == 0:
            status = "noop"
        else:
            status = "applied"
        if not dry_run and not failed:
            _record_manifest(migration_state, manifest_value)
        state_hash_after = canonical_contract_hash(working_state)
        replay_state = deepcopy(working_state)
        replay_rows = [apply_migration_step(replay_state, step) for step in step_rows]
        replay_failed = any(text_value(row.get("status")) == "failed" for row in replay_rows)
        state_hash_replay = canonical_contract_hash(replay_state)
        replay_safe = (not replay_failed) and (state_hash_after == state_hash_replay)
        if not dry_run and not failed:
            state.clear()
            state.update(working_state)

    report = {
        "schema_version": text_value(schema_version, default=MIGRATION_REPORT_SCHEMA_VERSION)
        or MIGRATION_REPORT_SCHEMA_VERSION,
        "manifest_schema_version": text_value(
            manifest_value.get("schema_version"),
            default=MIGRATION_MANIFEST_SCHEMA_VERSION,
        )
        or MIGRATION_MANIFEST_SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "manifest_name": text_value(manifest_value.get("name")),
        "dry_run": bool(dry_run),
        "status": status,
        "replay_safe": bool(replay_safe),
        "state_hash_before": state_hash_before,
        "state_hash_after": state_hash_after,
        "state_hash_replay": state_hash_replay,
        "step_results": normalize_step_result_rows(step_results),
        "summary": _normalize_summary(None, step_results=normalize_step_result_rows(step_results)),
        "extensions": merge_extensions(extensions),
    }
    return report


def normalize_migration_report(value: object) -> dict[str, object]:
    data = map_value(value)
    step_results = normalize_step_result_rows(data.get("step_results"))
    summary = _normalize_summary(data.get("summary"), step_results=step_results)
    status = text_value(data.get("status"), default="noop") or "noop"
    if status not in {"applied", "noop", "already_applied", "failed"}:
        status = "noop"
    return {
        "schema_version": text_value(data.get("schema_version"), default=MIGRATION_REPORT_SCHEMA_VERSION)
        or MIGRATION_REPORT_SCHEMA_VERSION,
        "manifest_schema_version": text_value(
            data.get("manifest_schema_version"),
            default=MIGRATION_MANIFEST_SCHEMA_VERSION,
        )
        or MIGRATION_MANIFEST_SCHEMA_VERSION,
        "manifest_id": text_value(data.get("manifest_id")),
        "manifest_name": text_value(data.get("manifest_name")),
        "dry_run": bool(data.get("dry_run")),
        "status": status,
        "replay_safe": bool(data.get("replay_safe")),
        "state_hash_before": text_value(data.get("state_hash_before")),
        "state_hash_after": text_value(data.get("state_hash_after")),
        "state_hash_replay": text_value(data.get("state_hash_replay")),
        "step_results": step_results,
        "summary": summary,
        "extensions": merge_extensions(data.get("extensions")),
    }


def _record_manifest(migration_state: dict[str, object], manifest: dict[str, object]) -> None:
    manifest_id = text_value(manifest.get("manifest_id"))
    applied_manifests = dict(migration_state.get("applied_manifests") or {})
    applied_steps = dict(migration_state.get("applied_steps") or {})
    applied_manifests[manifest_id] = {
        "manifest_id": manifest_id,
        "name": text_value(manifest.get("name")),
        "step_count": len(list(manifest.get("steps") or [])),
    }
    for step in manifest.get("steps") or []:
        step_id = text_value(step.get("step_id"))
        if step_id:
            applied_steps[step_id] = manifest_id
    migration_state["applied_manifests"] = _normalize_applied_manifests(applied_manifests)
    migration_state["applied_steps"] = _normalize_applied_steps(applied_steps)


def _normalize_applied_manifests(value: object) -> dict[str, dict[str, object]]:
    data = map_value(value)
    rows: dict[str, dict[str, object]] = {}
    for key in sorted(data.keys()):
        entry = map_value(data.get(key))
        manifest_id = text_value(entry.get("manifest_id") or key)
        if not manifest_id:
            continue
        rows[manifest_id] = {
            "manifest_id": manifest_id,
            "name": text_value(entry.get("name")),
            "step_count": int_value(entry.get("step_count"), default=0, minimum=0),
        }
    return rows


def _normalize_applied_steps(value: object) -> dict[str, str]:
    data = map_value(value)
    rows: dict[str, str] = {}
    for key in sorted(data.keys()):
        step_id = text_value(key)
        manifest_id = text_value(data.get(key))
        if not step_id or not manifest_id:
            continue
        rows[step_id] = manifest_id
    return rows


def _normalize_summary(value: object, *, step_results: list[dict[str, object]]) -> dict[str, int]:
    data = map_value(value)
    fallback = build_step_summary(step_results)
    return {
        "applied_steps": int_value(data.get("applied_steps"), default=fallback["applied_steps"], minimum=0),
        "failed_steps": int_value(data.get("failed_steps"), default=fallback["failed_steps"], minimum=0),
        "skipped_steps": int_value(data.get("skipped_steps"), default=fallback["skipped_steps"], minimum=0),
        "total_steps": int_value(data.get("total_steps"), default=fallback["total_steps"], minimum=0),
    }


__all__ = [
    "MIGRATION_REPORT_SCHEMA_VERSION",
    "MIGRATION_STATE_SCHEMA_VERSION",
    "build_migration_manifest",
    "build_migration_step",
    "ensure_migration_state",
    "normalize_migration_manifest",
    "normalize_migration_report",
    "normalize_migration_step",
    "run_migration_manifest",
]

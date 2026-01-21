from __future__ import annotations

from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.artifact_contract import ArtifactContract
from namel3ss.runtime.data.migration_planner import MigrationPlan, build_migration_plan
from namel3ss.runtime.data.migration_store import MigrationState, load_plan, load_state, write_plan, write_state
from namel3ss.schema.evolution import load_schema_snapshot, workspace_snapshot_path, write_workspace_snapshot
from namel3ss.schema.records import RecordSchema


def build_plan(records: list[RecordSchema], *, project_root: str | Path) -> MigrationPlan:
    previous = _load_previous_snapshot(project_root)
    return build_migration_plan(records, previous_snapshot=previous)


def status_payload(records: list[RecordSchema], *, project_root: str | Path) -> dict:
    plan = build_plan(records, project_root=project_root)
    state = load_state(project_root)
    pending = plan.summary.get("pending", False) and plan.plan_id != state.applied_plan_id
    plan_changed = bool(state.last_plan_id and state.last_plan_id != plan.plan_id)
    return {
        "ok": True,
        "plan_id": plan.plan_id,
        "pending": pending,
        "breaking": bool(plan.summary.get("breaking", False)),
        "reversible": bool(plan.summary.get("reversible", False)),
        "baseline": bool(plan.summary.get("baseline", False)),
        "change_count": int(plan.summary.get("change_count", 0)),
        "last_plan_id": state.last_plan_id,
        "applied_plan_id": state.applied_plan_id,
        "plan_changed": plan_changed,
    }


def plan_payload(records: list[RecordSchema], *, project_root: str | Path) -> dict:
    plan = build_plan(records, project_root=project_root)
    return {"ok": True, "plan": plan.as_dict()}


def apply_plan(
    records: list[RecordSchema],
    *,
    project_root: str | Path,
    store: object | None,
) -> dict:
    plan = build_plan(records, project_root=project_root)
    write_plan(project_root, plan.plan_id, plan.as_dict())
    next_state = MigrationState(last_plan_id=plan.plan_id, applied_plan_id=plan.plan_id)
    write_state(project_root, next_state)
    if store is not None:
        write_workspace_snapshot(records, project_root=project_root, store=store)
    return {
        "ok": True,
        "plan": plan.as_dict(),
        "state": next_state.as_dict(),
    }


def rollback_plan(
    *,
    project_root: str | Path,
) -> dict:
    state = load_state(project_root)
    if not state.applied_plan_id:
        raise Namel3ssError(_no_applied_message())
    plan = load_plan(project_root, state.applied_plan_id)
    if not isinstance(plan, dict):
        raise Namel3ssError(_missing_plan_message())
    summary = plan.get("summary") if isinstance(plan.get("summary"), dict) else {}
    if not summary.get("reversible", False):
        raise Namel3ssError(_unsafe_rollback_message())
    from_schema = plan.get("from_schema")
    if not isinstance(from_schema, dict):
        raise Namel3ssError(_missing_plan_message())
    _write_schema_snapshot(project_root, from_schema)
    next_state = MigrationState(last_plan_id=state.last_plan_id, applied_plan_id=None)
    write_state(project_root, next_state)
    return {
        "ok": True,
        "rolled_back": state.applied_plan_id,
        "state": next_state.as_dict(),
    }


def _load_previous_snapshot(project_root: str | Path) -> dict | None:
    path = workspace_snapshot_path(Path(project_root))
    if not path.exists():
        return None
    return load_schema_snapshot(path)


def _write_schema_snapshot(project_root: str | Path, snapshot: dict) -> Path:
    contract = ArtifactContract(Path(project_root) / ".namel3ss")
    path = contract.prepare_file("schema/last.json")
    payload = canonical_json_dumps(snapshot, pretty=True, drop_run_keys=False)
    path.write_text(payload, encoding="utf-8")
    return path


def _no_applied_message() -> str:
    return build_guidance_message(
        what="No applied migrations to roll back.",
        why="Rollback requires a previously applied migration plan.",
        fix="Apply a migration first or regenerate the plan.",
        example="n3 migrate plan",
    )


def _missing_plan_message() -> str:
    return build_guidance_message(
        what="Migration plan record is missing.",
        why="The applied plan file could not be found or parsed.",
        fix="Regenerate the migration plan before rolling back.",
        example="n3 migrate plan",
    )


def _unsafe_rollback_message() -> str:
    return build_guidance_message(
        what="Rollback is not safe for this migration plan.",
        why="The plan includes breaking changes that cannot be reversed safely.",
        fix="Apply a new migration plan or restore from a data export.",
        example="n3 data import data.json",
    )


__all__ = [
    "apply_plan",
    "build_plan",
    "plan_payload",
    "rollback_plan",
    "status_payload",
]

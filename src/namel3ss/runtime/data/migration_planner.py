from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.schema.evolution import SCHEMA_SNAPSHOT_VERSION, build_schema_snapshot, diff_schema_snapshots
from namel3ss.schema.records import RecordSchema


@dataclass(frozen=True)
class MigrationPlan:
    plan_id: str
    from_snapshot: dict
    to_snapshot: dict
    changes: tuple[dict, ...]
    breaking: tuple[dict, ...]
    summary: dict

    def as_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "from_schema": self.from_snapshot,
            "to_schema": self.to_snapshot,
            "changes": list(self.changes),
            "breaking": list(self.breaking),
            "summary": dict(self.summary),
        }


def build_migration_plan(
    records: Iterable[RecordSchema],
    *,
    previous_snapshot: dict | None,
) -> MigrationPlan:
    baseline = previous_snapshot is None
    from_snapshot = previous_snapshot or _empty_snapshot()
    to_snapshot = build_schema_snapshot(records)
    diff = diff_schema_snapshots(to_snapshot, from_snapshot)
    changes = tuple(change.as_dict() for change in diff.changes)
    breaking = tuple(change.as_dict() for change in diff.breaking)
    summary = {
        "pending": bool(changes),
        "change_count": len(changes),
        "breaking": bool(breaking),
        "reversible": not bool(breaking),
        "baseline": baseline,
    }
    plan_id = _plan_id(from_snapshot, to_snapshot, changes)
    return MigrationPlan(
        plan_id=plan_id,
        from_snapshot=from_snapshot,
        to_snapshot=to_snapshot,
        changes=changes,
        breaking=breaking,
        summary=summary,
    )


def _empty_snapshot() -> dict:
    return {"schema_version": SCHEMA_SNAPSHOT_VERSION, "records": []}


def _plan_id(from_snapshot: dict, to_snapshot: dict, changes: tuple[dict, ...]) -> str:
    payload = {"from": from_snapshot, "to": to_snapshot, "changes": list(changes)}
    digest = sha256(
        canonical_json_dumps(payload, pretty=False, drop_run_keys=False).encode("utf-8")
    ).hexdigest()[:12]
    return f"plan-{digest}"


__all__ = ["MigrationPlan", "build_migration_plan"]

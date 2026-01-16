from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Sequence

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.artifact_contract import ArtifactContract
from namel3ss.schema.records import FieldConstraint, FieldSchema, RecordSchema
from namel3ss.validation import add_warning


SCHEMA_SNAPSHOT_VERSION = "records.v1"
WORKSPACE_SCHEMA_DIR = "schema"
WORKSPACE_SCHEMA_FILENAME = "last.json"
BUILD_SCHEMA_DIR = "schema"
BUILD_SCHEMA_FILENAME = "records.json"


@dataclass(frozen=True)
class SchemaChange:
    kind: str
    record: str
    field: str | None = None
    before: object | None = None
    after: object | None = None
    breaking: bool = True

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "record": self.record,
            "field": self.field,
            "before": self.before,
            "after": self.after,
            "breaking": self.breaking,
        }


@dataclass(frozen=True)
class SchemaDiff:
    changes: tuple[SchemaChange, ...]
    breaking: tuple[SchemaChange, ...]

    @property
    def has_breaking(self) -> bool:
        return bool(self.breaking)


def build_schema_snapshot(records: Iterable[RecordSchema]) -> dict:
    return {
        "schema_version": SCHEMA_SNAPSHOT_VERSION,
        "records": [
            _record_payload(record)
            for record in sorted(records, key=lambda item: item.name)
            if getattr(record, "name", None)
        ],
    }


def workspace_snapshot_path(project_root: Path) -> Path:
    return Path(project_root) / ".namel3ss" / WORKSPACE_SCHEMA_DIR / WORKSPACE_SCHEMA_FILENAME


def build_snapshot_path(build_path: Path) -> Path:
    return Path(build_path) / BUILD_SCHEMA_DIR / BUILD_SCHEMA_FILENAME


def load_schema_snapshot(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Schema snapshot is invalid at {path.as_posix()}.",
                why="The snapshot is not valid JSON.",
                fix="Delete the snapshot file and re-run the app to regenerate it.",
                example=f"rm {path.as_posix()}",
            )
        ) from err
    if not isinstance(data, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Schema snapshot is not an object.",
                why="Snapshots must be JSON objects.",
                fix="Delete the snapshot file and re-run the app to regenerate it.",
                example=f"rm {path.as_posix()}",
            )
        )
    version = data.get("schema_version")
    if version != SCHEMA_SNAPSHOT_VERSION:
        raise Namel3ssError(
            build_guidance_message(
                what="Schema snapshot version is not supported.",
                why=f"Expected {SCHEMA_SNAPSHOT_VERSION}, got {version}.",
                fix="Delete the snapshot file and re-run the app to regenerate it.",
                example=f"rm {path.as_posix()}",
            )
        )
    records = data.get("records")
    if not isinstance(records, list):
        raise Namel3ssError(
            build_guidance_message(
                what="Schema snapshot records are missing.",
                why="Snapshots must include a records list.",
                fix="Delete the snapshot file and re-run the app to regenerate it.",
                example=f"rm {path.as_posix()}",
            )
        )
    return data


def diff_schema_snapshots(current: dict, previous: dict) -> SchemaDiff:
    changes: list[SchemaChange] = []
    current_records = _record_map(current)
    previous_records = _record_map(previous)

    for record_name in sorted(previous_records.keys()):
        if record_name not in current_records:
            changes.append(SchemaChange(kind="record_removed", record=record_name))

    for record_name in sorted(current_records.keys()):
        if record_name not in previous_records:
            changes.append(SchemaChange(kind="record_added", record=record_name, breaking=False))

    for record_name in sorted(set(current_records) & set(previous_records)):
        current_record = current_records[record_name]
        previous_record = previous_records[record_name]
        _diff_record_settings(record_name, current_record, previous_record, changes)
        _diff_record_fields(record_name, current_record, previous_record, changes)

    ordered = sorted(changes, key=lambda change: (change.record, change.field or "", change.kind))
    breaking = tuple(change for change in ordered if change.breaking)
    return SchemaDiff(changes=tuple(ordered), breaking=breaking)


def append_schema_evolution_warnings(program, warnings: list | None) -> None:
    if warnings is None:
        return
    root = getattr(program, "project_root", None)
    if not root:
        return
    snapshot_path = workspace_snapshot_path(Path(root))
    try:
        previous = load_schema_snapshot(snapshot_path)
    except Namel3ssError as err:
        first_line = str(err).splitlines()[0] if str(err) else "Schema snapshot is invalid."
        add_warning(
            warnings,
            code="schema.snapshot.invalid",
            message=first_line,
            fix="Delete the snapshot file and re-run the app to regenerate it.",
            enforced_at="runtime",
            category="schema",
        )
        return
    if not previous:
        return
    current = build_schema_snapshot(getattr(program, "records", []))
    diff = diff_schema_snapshots(current, previous)
    for change in diff.breaking:
        add_warning(
            warnings,
            code="schema.breaking",
            message=f"Schema change is incompatible: {_format_change(change)}.",
            fix="Revert the schema change or reset the persisted data store.",
            enforced_at="runtime",
            category="schema",
        )


def enforce_schema_compatibility(
    records: Iterable[RecordSchema],
    *,
    previous_snapshot: dict | None,
    context: str,
) -> None:
    if not previous_snapshot:
        return
    current = build_schema_snapshot(records)
    diff = diff_schema_snapshots(current, previous_snapshot)
    if diff.has_breaking:
        raise _schema_incompatible_error(diff.breaking, context=context)


def enforce_runtime_schema_compatibility(
    records: Iterable[RecordSchema],
    *,
    project_root: str | Path | None,
    store: object | None,
) -> None:
    if project_root is None:
        return
    if not _persistence_enabled(store):
        return
    snapshot_path = workspace_snapshot_path(Path(project_root))
    previous = load_schema_snapshot(snapshot_path)
    enforce_schema_compatibility(records, previous_snapshot=previous, context="runtime")


def write_workspace_snapshot(
    records: Iterable[RecordSchema],
    *,
    project_root: str | Path | None,
    store: object | None,
) -> Path | None:
    if project_root is None:
        return None
    if not _persistence_enabled(store):
        return None
    contract = ArtifactContract(Path(project_root) / ".namel3ss")
    snapshot = build_schema_snapshot(records)
    path = contract.prepare_file(f"{WORKSPACE_SCHEMA_DIR}/{WORKSPACE_SCHEMA_FILENAME}")
    path.write_text(canonical_json_dumps(snapshot, pretty=True), encoding="utf-8")
    return path


def _record_payload(record: RecordSchema) -> dict:
    payload = {
        "name": record.name,
        "fields": [
            _field_payload(field)
            for field in sorted(record.fields, key=lambda item: item.name)
        ],
    }
    if record.tenant_key:
        payload["tenant_key"] = list(record.tenant_key)
    if record.ttl_hours is not None:
        payload["ttl_hours"] = record.ttl_hours
    return payload


def _field_payload(field: FieldSchema) -> dict:
    payload = {"name": field.name, "type": field.type_name}
    constraint = _constraint_payload(field.constraint)
    if constraint is not None:
        payload["constraint"] = constraint
    return payload


def _constraint_payload(constraint: FieldConstraint | None) -> dict | None:
    if constraint is None:
        return None
    payload: dict[str, object] = {"kind": constraint.kind}
    if constraint.pattern:
        payload["pattern"] = constraint.pattern
    if constraint.expression is not None:
        payload["value"] = _literal_value(constraint.expression)
    if constraint.expression_high is not None:
        payload["high"] = _literal_value(constraint.expression_high)
    return payload


def _literal_value(expr: ir.Expression) -> object:
    if isinstance(expr, ir.Literal):
        return expr.value
    if isinstance(expr, ir.UnaryOp) and expr.op in {"+", "-"} and isinstance(expr.operand, ir.Literal):
        value = expr.operand.value
        try:
            return value if expr.op == "+" else -value
        except Exception:
            return value
    return str(expr)


def _record_map(snapshot: dict) -> dict[str, dict]:
    records = snapshot.get("records") if isinstance(snapshot, dict) else None
    if not isinstance(records, list):
        return {}
    return {record.get("name"): record for record in records if isinstance(record, dict) and record.get("name")}


def _field_map(record: dict) -> dict[str, dict]:
    fields = record.get("fields") if isinstance(record, dict) else None
    if not isinstance(fields, list):
        return {}
    return {field.get("name"): field for field in fields if isinstance(field, dict) and field.get("name")}


def _diff_record_settings(record_name: str, current: dict, previous: dict, changes: list[SchemaChange]) -> None:
    current_tenant = current.get("tenant_key")
    previous_tenant = previous.get("tenant_key")
    if current_tenant != previous_tenant:
        changes.append(
            SchemaChange(
                kind="record_tenant_key_changed",
                record=record_name,
                before=_tenant_label(previous_tenant),
                after=_tenant_label(current_tenant),
            )
        )
    current_ttl = current.get("ttl_hours")
    previous_ttl = previous.get("ttl_hours")
    if current_ttl != previous_ttl:
        changes.append(
            SchemaChange(
                kind="record_ttl_changed",
                record=record_name,
                before=_value_label(previous_ttl),
                after=_value_label(current_ttl),
            )
        )


def _diff_record_fields(record_name: str, current: dict, previous: dict, changes: list[SchemaChange]) -> None:
    current_fields = _field_map(current)
    previous_fields = _field_map(previous)

    for field_name in sorted(previous_fields.keys()):
        if field_name not in current_fields:
            changes.append(SchemaChange(kind="field_removed", record=record_name, field=field_name))

    for field_name in sorted(current_fields.keys()):
        if field_name not in previous_fields:
            constraint = current_fields[field_name].get("constraint")
            required = _field_is_required(constraint)
            changes.append(
                SchemaChange(
                    kind="field_added_required" if required else "field_added_optional",
                    record=record_name,
                    field=field_name,
                    breaking=required,
                )
            )

    for field_name in sorted(set(current_fields) & set(previous_fields)):
        current_field = current_fields[field_name]
        previous_field = previous_fields[field_name]
        current_type = current_field.get("type")
        previous_type = previous_field.get("type")
        if current_type != previous_type:
            changes.append(
                SchemaChange(
                    kind="field_type_changed",
                    record=record_name,
                    field=field_name,
                    before=_value_label(previous_type),
                    after=_value_label(current_type),
                )
            )
        current_constraint = current_field.get("constraint")
        previous_constraint = previous_field.get("constraint")
        if _constraint_signature(current_constraint) != _constraint_signature(previous_constraint):
            changes.append(
                SchemaChange(
                    kind="field_constraint_changed",
                    record=record_name,
                    field=field_name,
                    before=_constraint_label(previous_constraint),
                    after=_constraint_label(current_constraint),
                )
            )


def _constraint_signature(payload: object) -> tuple:
    if not isinstance(payload, dict):
        return ("none",)
    return (
        payload.get("kind"),
        payload.get("value"),
        payload.get("high"),
        payload.get("pattern"),
    )


def _field_is_required(constraint: object) -> bool:
    if not isinstance(constraint, dict):
        return False
    kind = str(constraint.get("kind") or "").strip().lower()
    if not kind:
        return False
    return kind not in {"unique"}


def _schema_incompatible_error(changes: Sequence[SchemaChange], *, context: str) -> Namel3ssError:
    change_lines = [_format_change(change) for change in changes]
    what = "Stored data schema is incompatible with the current app schema."
    why = "Breaking changes detected:\n" + "\n".join(_bulleted(change_lines))
    fix = "Revert the schema change or reset the persisted data store."
    example = "n3 data reset"
    return Namel3ssError(
        build_guidance_message(what=what, why=why, fix=fix, example=example),
        details={
            "category": "policy",
            "code": "schema.incompatible",
            "context": context,
            "changes": [change.as_dict() for change in changes],
        },
    )


def _format_change(change: SchemaChange) -> str:
    if change.kind == "record_removed":
        return f'record "{change.record}" was removed'
    if change.kind == "record_added":
        return f'record "{change.record}" was added'
    if change.kind == "record_tenant_key_changed":
        return f'record "{change.record}" tenant_key changed from {change.before} to {change.after}'
    if change.kind == "record_ttl_changed":
        return f'record "{change.record}" ttl_hours changed from {change.before} to {change.after}'
    if change.kind == "field_removed":
        return f'record "{change.record}" field "{change.field}" was removed'
    if change.kind == "field_added_required":
        return f'record "{change.record}" added required field "{change.field}"'
    if change.kind == "field_added_optional":
        return f'record "{change.record}" added optional field "{change.field}"'
    if change.kind == "field_type_changed":
        return (
            f'record "{change.record}" field "{change.field}" changed type '
            f"from {change.before} to {change.after}"
        )
    if change.kind == "field_constraint_changed":
        return (
            f'record "{change.record}" field "{change.field}" changed constraints '
            f"from {change.before} to {change.after}"
        )
    return f"{change.kind} on record {change.record}"


def _constraint_label(payload: object) -> str:
    if not isinstance(payload, dict):
        return "none"
    kind = str(payload.get("kind") or "none")
    if kind == "pattern":
        pattern = payload.get("pattern")
        return f'pattern "{pattern}"' if pattern else "pattern"
    if kind == "between":
        return f"between {payload.get('value')} and {payload.get('high')}"
    if kind in {"gt", "gte", "lt", "lte", "len_min", "len_max"}:
        value = payload.get("value")
        return f"{kind} {value}"
    return kind


def _tenant_label(value: object) -> str:
    if isinstance(value, list):
        joined = ".".join(str(item) for item in value)
        return f"identity.{joined}" if joined else "none"
    return "none" if value in {None, ""} else str(value)


def _value_label(value: object) -> str:
    return "none" if value is None else str(value)


def _bulleted(lines: Iterable[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines if line]


def _persistence_enabled(store: object | None) -> bool:
    if store is None:
        return False
    getter = getattr(store, "get_metadata", None)
    if not callable(getter):
        return False
    meta = getter()
    enabled = getattr(meta, "enabled", None) if meta is not None else None
    if isinstance(enabled, bool):
        return enabled
    if isinstance(meta, dict):
        return bool(meta.get("enabled", False))
    return False


__all__ = [
    "BUILD_SCHEMA_DIR",
    "BUILD_SCHEMA_FILENAME",
    "SCHEMA_SNAPSHOT_VERSION",
    "SchemaChange",
    "SchemaDiff",
    "append_schema_evolution_warnings",
    "build_schema_snapshot",
    "build_snapshot_path",
    "diff_schema_snapshots",
    "enforce_runtime_schema_compatibility",
    "enforce_schema_compatibility",
    "load_schema_snapshot",
    "workspace_snapshot_path",
    "write_workspace_snapshot",
]

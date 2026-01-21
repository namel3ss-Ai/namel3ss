from __future__ import annotations

from types import SimpleNamespace

from namel3ss.runtime.data.data_routes import build_migrations_plan_payload
from namel3ss.runtime.data.migration_planner import build_migration_plan
from namel3ss.runtime.data.migration_runner import apply_plan, status_payload
from namel3ss.runtime.data.migration_store import MigrationState, write_plan, write_state
from namel3ss.schema.evolution import build_schema_snapshot
from namel3ss.schema.records import FieldSchema, RecordSchema


def _records_v1() -> list[RecordSchema]:
    return [RecordSchema(name="Alpha", fields=[FieldSchema(name="id", type_name="text")])]


def _records_v2() -> list[RecordSchema]:
    return [
        RecordSchema(
            name="Alpha",
            fields=[
                FieldSchema(name="id", type_name="text"),
                FieldSchema(name="name", type_name="text"),
            ],
        ),
        RecordSchema(name="Beta", fields=[FieldSchema(name="id", type_name="text")]),
    ]


def test_migration_plan_is_deterministic_and_ordered() -> None:
    previous = build_schema_snapshot(_records_v1())
    plan_one = build_migration_plan(_records_v2(), previous_snapshot=previous)
    plan_two = build_migration_plan(_records_v2(), previous_snapshot=previous)
    assert plan_one.plan_id == plan_two.plan_id
    assert plan_one.changes == plan_two.changes
    assert [change["kind"] for change in plan_one.changes] == [
        "field_added_optional",
        "record_added",
    ]


def test_migration_status_is_deterministic(tmp_path) -> None:
    records = _records_v2()
    status_one = status_payload(records, project_root=tmp_path)
    status_two = status_payload(records, project_root=tmp_path)
    assert status_one == status_two
    assert status_one["plan_id"]


def test_apply_plan_is_deterministic(tmp_path) -> None:
    root_one = tmp_path / "one"
    root_two = tmp_path / "two"
    root_one.mkdir()
    root_two.mkdir()
    records = _records_v2()
    payload_one = apply_plan(records, project_root=root_one, store=None)
    payload_two = apply_plan(records, project_root=root_two, store=None)
    assert payload_one["plan"]["plan_id"] == payload_two["plan"]["plan_id"]
    assert (root_one / ".namel3ss" / "migrations" / "state.json").exists()
    assert (root_one / ".namel3ss" / "migrations" / "plans").exists()


def test_migrations_plan_payload_prefers_stored_plan(tmp_path) -> None:
    plan_id = "plan-test"
    plan = {"plan_id": plan_id, "summary": {}}
    write_plan(tmp_path, plan_id, plan)
    write_state(tmp_path, MigrationState(last_plan_id=plan_id, applied_plan_id=None))
    program = SimpleNamespace(records=[])
    payload = build_migrations_plan_payload(program, project_root=tmp_path)
    assert payload["plan"]["plan_id"] == plan_id

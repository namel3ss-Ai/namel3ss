from namel3ss.schema.evolution import build_schema_snapshot, diff_schema_snapshots
from namel3ss.schema.records import FieldConstraint, FieldSchema, RecordSchema


def _record(name: str, fields: list[FieldSchema]) -> RecordSchema:
    return RecordSchema(name=name, fields=fields)


def test_schema_diff_allows_optional_field() -> None:
    before = build_schema_snapshot([_record("Note", [FieldSchema(name="title", type_name="text")])])
    after = build_schema_snapshot(
        [_record("Note", [FieldSchema(name="title", type_name="text"), FieldSchema(name="tag", type_name="text")])]
    )
    diff = diff_schema_snapshots(after, before)
    assert diff.breaking == ()


def test_schema_diff_breaks_on_required_field_addition() -> None:
    before = build_schema_snapshot([_record("Note", [FieldSchema(name="title", type_name="text")])])
    required = FieldSchema(name="status", type_name="text", constraint=FieldConstraint(kind="present"))
    after = build_schema_snapshot([_record("Note", [FieldSchema(name="title", type_name="text"), required])])
    diff = diff_schema_snapshots(after, before)
    assert any(change.kind == "field_added_required" for change in diff.breaking)


def test_schema_diff_breaks_on_field_removal() -> None:
    before = build_schema_snapshot(
        [_record("Note", [FieldSchema(name="title", type_name="text"), FieldSchema(name="body", type_name="text")])]
    )
    after = build_schema_snapshot([_record("Note", [FieldSchema(name="title", type_name="text")])])
    diff = diff_schema_snapshots(after, before)
    assert any(change.kind == "field_removed" for change in diff.breaking)


def test_schema_diff_breaks_on_type_change() -> None:
    before = build_schema_snapshot([_record("Note", [FieldSchema(name="title", type_name="text")])])
    after = build_schema_snapshot([_record("Note", [FieldSchema(name="title", type_name="number")])])
    diff = diff_schema_snapshots(after, before)
    assert any(change.kind == "field_type_changed" for change in diff.breaking)


def test_schema_diff_ordering_is_stable() -> None:
    before = build_schema_snapshot(
        [
            _record("Alpha", [FieldSchema(name="value", type_name="text")]),
            _record("Beta", [FieldSchema(name="value", type_name="text")]),
        ]
    )
    after = build_schema_snapshot([_record("Alpha", [FieldSchema(name="value", type_name="number")])])
    diff = diff_schema_snapshots(after, before)
    ordered = [(change.record, change.field, change.kind) for change in diff.breaking]
    assert ordered == [
        ("Alpha", "value", "field_type_changed"),
        ("Beta", None, "record_removed"),
    ]

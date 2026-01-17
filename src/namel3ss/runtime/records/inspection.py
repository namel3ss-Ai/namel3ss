from __future__ import annotations

from typing import Iterable

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.records.ordering import normalize_record_id, record_id_field, sort_records, sorted_record_ids
from namel3ss.runtime.records.service import build_record_scope
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema.records import RecordSchema


DEFAULT_RECORD_LIMIT = 50


def collect_record_rows(
    schemas: Iterable[RecordSchema],
    store: Storage,
    identity: dict | None,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    rows: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}
    for schema in schemas:
        try:
            scope = build_record_scope(schema, identity)
            records = store.find(schema, lambda _rec: True, scope=scope)
            rows[schema.name] = sort_records(schema, records)
        except Namel3ssError as exc:
            rows[schema.name] = []
            errors[schema.name] = str(exc)
    return rows, errors


def build_records_payload(
    schemas: Iterable[RecordSchema],
    rows: dict[str, list[dict]],
    errors: dict[str, str] | None = None,
    *,
    limit: int | None = DEFAULT_RECORD_LIMIT,
) -> list[dict]:
    payload: list[dict] = []
    for schema in schemas:
        data_rows = list(rows.get(schema.name, []))
        if limit is None:
            entry_rows = data_rows
        else:
            entry_rows = data_rows[: max(limit, 0)]
        entry = {
            "name": schema.name,
            "id_field": record_id_field(schema),
            "fields": [{"name": field.name, "type": field.type_name} for field in schema.fields],
            "count": len(data_rows),
            "rows": entry_rows,
        }
        if errors and schema.name in errors:
            entry["error"] = errors[schema.name]
        if limit is not None and len(data_rows) > len(entry_rows):
            entry["limit"] = len(entry_rows)
            entry["truncated"] = True
        payload.append(entry)
    return payload


def build_record_effects(
    schemas: Iterable[RecordSchema],
    before_rows: dict[str, list[dict]],
    after_rows: dict[str, list[dict]],
) -> list[dict]:
    effects: list[dict] = []
    for schema in schemas:
        before = before_rows.get(schema.name, [])
        after = after_rows.get(schema.name, [])
        effects.extend(_diff_records(schema, before, after))
    return effects


def _diff_records(schema: RecordSchema, before: list[dict], after: list[dict]) -> list[dict]:
    id_field = record_id_field(schema)
    before_index = _index_records(before, id_field)
    after_index = _index_records(after, id_field)
    created_ids = [after_index[key]["id"] for key in after_index.keys() - before_index.keys()]
    deleted_ids = [before_index[key]["id"] for key in before_index.keys() - after_index.keys()]
    updated_ids: list[object] = []
    for key in before_index.keys() & after_index.keys():
        if _record_fingerprint(before_index[key]["row"]) != _record_fingerprint(after_index[key]["row"]):
            updated_ids.append(after_index[key]["id"])
    effects: list[dict] = []
    for action, ids in (("create", created_ids), ("update", updated_ids), ("delete", deleted_ids)):
        if not ids:
            continue
        effects.append(
            {
                "record": schema.name,
                "action": action,
                "count": len(ids),
                "ids": sorted_record_ids(ids),
            }
        )
    return effects


def _index_records(rows: list[dict], id_field: str) -> dict[object, dict]:
    index: dict[object, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        record_id = row.get(id_field)
        if record_id is None:
            continue
        key = normalize_record_id(record_id)
        index[key] = {"id": record_id, "row": row}
    return index


def _record_fingerprint(record: dict) -> str:
    try:
        return canonical_json_dumps(record, pretty=False)
    except Exception:
        return str(record)


__all__ = [
    "DEFAULT_RECORD_LIMIT",
    "build_record_effects",
    "build_records_payload",
    "collect_record_rows",
]

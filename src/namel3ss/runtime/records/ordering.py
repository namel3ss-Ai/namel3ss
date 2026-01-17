from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Tuple

from namel3ss.determinism import canonical_json_dumps
from namel3ss.schema.records import RecordSchema
from namel3ss.utils.numbers import decimal_is_int, decimal_to_str, is_number, to_decimal


def record_id_field(schema: RecordSchema) -> str:
    return "id" if "id" in schema.field_map else "_id"


def record_id_value(record: object, id_field: str) -> object | None:
    if isinstance(record, dict):
        return record.get(id_field)
    return None


def sort_records(schema: RecordSchema, records: list[dict]) -> list[dict]:
    id_field = record_id_field(schema)
    return sorted(records, key=lambda rec: _record_sort_key(rec, id_field))


def sorted_record_ids(values: Iterable[object]) -> list[object]:
    items: list[Tuple[object, tuple[int, int, object]]] = []
    for value in values:
        items.append((value, _value_sort_key(value)))
    items.sort(key=lambda item: item[1])
    return [normalize_record_id(item[0]) for item in items]


def normalize_record_id(value: object) -> object:
    if isinstance(value, Decimal):
        if decimal_is_int(value):
            return int(value)
        return decimal_to_str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _record_sort_key(record: object, id_field: str) -> tuple[int, int, object]:
    value = record_id_value(record, id_field)
    if value is not None:
        return _value_sort_key(value)
    try:
        return (2, 0, canonical_json_dumps(record, pretty=False))
    except Exception:
        return (2, 1, str(record))


def _value_sort_key(value: object) -> tuple[int, int, object]:
    if value is None:
        return (1, 0, "")
    if is_number(value) and not isinstance(value, bool):
        return (0, 0, to_decimal(value))
    if isinstance(value, str):
        return (0, 1, value)
    return (0, 2, str(value))


__all__ = [
    "normalize_record_id",
    "record_id_field",
    "record_id_value",
    "sort_records",
    "sorted_record_ids",
]

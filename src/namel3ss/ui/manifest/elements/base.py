from __future__ import annotations

from typing import Dict

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.utils.numbers import is_number, to_decimal


def _base_element(element_id: str, page_name: str, page_slug: str, index: int, item: ir.PageItem) -> dict:
    return {
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }


def _require_record(name: str, record_map: Dict[str, schema.RecordSchema], item: ir.PageItem) -> schema.RecordSchema:
    if name not in record_map:
        raise Namel3ssError(
            f"Page references unknown record '{name}'. Add the record or update the reference.",
            line=item.line,
            column=item.column,
        )
    return record_map[name]


def _view_representation(record: schema.RecordSchema) -> str:
    field_count = len(record.fields)
    if field_count == 0:
        return "list"
    if field_count <= 3:
        return "list"
    return "table"


def _stable_rows_by_id(rows: list[dict], id_field: str) -> list[dict]:
    if len(rows) <= 1:
        return rows

    def _key(row: dict) -> tuple[int, int, object]:
        if isinstance(row, dict):
            value = row.get(id_field)
            if value is not None:
                if is_number(value) and not isinstance(value, bool):
                    return (0, 0, to_decimal(value))
                if isinstance(value, str):
                    return (0, 1, value)
                return (0, 2, str(value))
        try:
            return (1, 0, canonical_json_dumps(row, pretty=False))
        except Exception:
            return (1, 0, str(row))

    return sorted(rows, key=_key)


__all__ = ["_base_element", "_require_record", "_stable_rows_by_id", "_view_representation"]

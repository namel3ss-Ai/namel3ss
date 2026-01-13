from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.utils.numbers import is_number, to_decimal
from namel3ss.ui.manifest_overlay import _drawer_id, _modal_id


def _table_id(page_slug: str, record_name: str) -> str:
    return f"page.{page_slug}.table.{_slugify(record_name)}"


def _table_row_action_id(element_id: str, label: str) -> str:
    return f"{element_id}.row_action.{_slugify(label)}"


def _table_id_field(record: schema.RecordSchema) -> str:
    return "id" if "id" in record.field_map else "_id"


def _resolve_table_columns(
    record: schema.RecordSchema,
    directives: list[ir.TableColumnDirective] | None,
) -> list[dict]:
    if not directives:
        return [{"name": f.name, "type": f.type_name} for f in record.fields]
    include = [d.name for d in directives if d.kind == "include"]
    exclude = {d.name for d in directives if d.kind == "exclude"}
    labels = {d.name: d.label for d in directives if d.kind == "label" and d.label}
    if include:
        ordered = [name for name in include if name not in exclude]
    else:
        ordered = [f.name for f in record.fields if f.name not in exclude]
    columns: list[dict] = []
    for name in ordered:
        field = record.field_map.get(name)
        if field is None:
            continue
        entry = {"name": field.name, "type": field.type_name}
        label = labels.get(name)
        if label:
            entry["label"] = label
        columns.append(entry)
    return columns


def _apply_table_sort(
    rows: list[dict],
    sort: ir.TableSort,
    record: schema.RecordSchema,
) -> list[dict]:
    field = record.field_map.get(sort.by)
    if field is None:
        raise Namel3ssError(
            f"Table sort references unknown field '{sort.by}' in record '{record.name}'",
            line=sort.line,
            column=sort.column,
        )

    def _sort_key(row: dict):
        if sort.by not in row or row.get(sort.by) is None:
            raise Namel3ssError(
                f"Table sort field '{sort.by}' is missing in rows for record '{record.name}'",
                line=sort.line,
                column=sort.column,
            )
        value = row.get(sort.by)
        type_name = field.type_name.lower()
        if type_name in {"text", "string", "str"}:
            if not isinstance(value, str):
                raise Namel3ssError(
                    f"Table sort field '{sort.by}' must be text",
                    line=sort.line,
                    column=sort.column,
                )
            return value
        if type_name in {"number", "int", "integer"}:
            if not is_number(value):
                raise Namel3ssError(
                    f"Table sort field '{sort.by}' must be numeric",
                    line=sort.line,
                    column=sort.column,
                )
            return to_decimal(value)
        if type_name in {"boolean", "bool"}:
            if not isinstance(value, bool):
                raise Namel3ssError(
                    f"Table sort field '{sort.by}' must be boolean",
                    line=sort.line,
                    column=sort.column,
                )
            return 1 if value else 0
        raise Namel3ssError(
            f"Table sort field '{sort.by}' is not comparable",
            line=sort.line,
            column=sort.column,
        )

    reverse = sort.order == "desc"
    return sorted(rows, key=_sort_key, reverse=reverse)


def _apply_table_pagination(rows: list[dict], pagination: ir.TablePagination) -> list[dict]:
    if pagination.page_size <= 0:
        return rows
    return rows[: pagination.page_size]


def _build_row_actions(
    element_id: str,
    page_slug: str,
    actions: list[ir.TableRowAction] | None,
) -> tuple[list[dict], Dict[str, dict]]:
    if not actions:
        return [], {}
    seen: set[str] = set()
    entries: list[dict] = []
    action_map: Dict[str, dict] = {}
    for action in actions:
        action_id = _table_row_action_id(element_id, action.label)
        if action_id in seen:
            raise Namel3ssError(
                f"Row action '{action.label}' collides with another action id",
                line=action.line,
                column=action.column,
            )
        seen.add(action_id)
        if action.kind == "call_flow":
            entry = {"id": action_id, "type": "call_flow", "flow": action.flow_name}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "flow": action.flow_name})
            continue
        if action.kind in {"open_modal", "close_modal"}:
            target = _modal_id(page_slug, action.target or "")
            entry = {"id": action_id, "type": action.kind, "target": target}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "type": action.kind, "target": target})
            continue
        if action.kind in {"open_drawer", "close_drawer"}:
            target = _drawer_id(page_slug, action.target or "")
            entry = {"id": action_id, "type": action.kind, "target": target}
            action_map[action_id] = entry
            entries.append({"id": action_id, "label": action.label, "type": action.kind, "target": target})
            continue
        raise Namel3ssError(
            f"Row action '{action.label}' is not supported",
            line=action.line,
            column=action.column,
        )
    return entries, action_map


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed


__all__ = [
    "_table_id",
    "_table_row_action_id",
    "_table_id_field",
    "_resolve_table_columns",
    "_apply_table_sort",
    "_apply_table_pagination",
    "_build_row_actions",
]

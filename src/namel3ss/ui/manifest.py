from __future__ import annotations

from typing import Dict, List, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.schema import records as schema


def build_manifest(program: ir.Program, *, state: dict | None = None, store: MemoryStore | None = None) -> dict:
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in program.records}
    pages = []
    actions: Dict[str, dict] = {}
    state = state or {}
    for page in program.pages:
        page_slug = _slugify(page.name)
        elements = []
        for idx, item in enumerate(page.items):
            element, action_entry = _page_item_to_manifest(item, record_map, page.name, page_slug, idx, store)
            elements.append(element)
            if action_entry:
                actions[action_entry["id"]] = action_entry
        pages.append(
            {
                "name": page.name,
                "slug": page_slug,
                "elements": elements,
            }
        )
    return {"pages": pages, "actions": actions}


def _page_item_to_manifest(
    item: ir.PageItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    index: int,
    store: MemoryStore | None,
) -> tuple[dict, dict | None]:
    if isinstance(item, ir.TitleItem):
        element_id = _title_element_id(page_slug, index)
        return (
            {
                "type": "title",
                "value": item.value,
                "element_id": element_id,
                "page": page_name,
                "page_slug": page_slug,
                "index": index,
                "line": item.line,
                "column": item.column,
            },
            None,
        )
    if isinstance(item, ir.TextItem):
        element_id = _text_element_id(page_slug, index)
        return (
            {
                "type": "text",
                "value": item.value,
                "element_id": element_id,
                "page": page_name,
                "page_slug": page_slug,
                "index": index,
                "line": item.line,
                "column": item.column,
            },
            None,
        )
    if isinstance(item, ir.FormItem):
        record = _require_record(item.record_name, record_map, item)
        action_id = _form_action_id(page_name, item.record_name)
        return (
            {
                "type": "form",
                "element_id": _form_element_id(page_slug, index),
                "id": action_id,
                "action_id": action_id,
                "record": record.name,
                "fields": [_field_to_manifest(f) for f in record.fields],
                "page": page_name,
                "page_slug": page_slug,
                "index": index,
                "line": item.line,
                "column": item.column,
            },
            {"id": action_id, "type": "submit_form", "record": record.name},
        )
    if isinstance(item, ir.TableItem):
        record = _require_record(item.record_name, record_map, item)
        table_id = _table_id(page_name, item.record_name)
        rows = []
        if store is not None:
            rows = store.list_records(record)[:20]
        return (
            {
                "type": "table",
                "id": table_id,
                "record": record.name,
                "columns": [{"name": f.name, "type": f.type_name} for f in record.fields],
                "rows": rows,
                "element_id": _table_element_id(page_slug, index),
                "page": page_name,
                "page_slug": page_slug,
                "index": index,
                "line": item.line,
                "column": item.column,
            },
            None,
        )
    if isinstance(item, ir.ButtonItem):
        action_id = _button_action_id(page_name, item.label)
        action_entry = {"id": action_id, "type": "call_flow", "flow": item.flow_name}
        element_id = _button_element_id(page_slug, index)
        element = {
            "type": "button",
            "label": item.label,
            "id": action_id,
            "action_id": action_id,
            "action": {"type": "call_flow", "flow": item.flow_name},
            "element_id": element_id,
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return element, action_entry
    raise Namel3ssError(f"Unsupported page item '{type(item)}'")


def _field_to_manifest(field: schema.FieldSchema) -> dict:
    return {
        "name": field.name,
        "type": field.type_name,
        "constraints": _constraints_to_manifest(field.constraint),
    }


def _constraints_to_manifest(constraint: Optional[schema.FieldConstraint]) -> List[dict]:
    if constraint is None:
        return []
    kind = constraint.kind
    if kind == "present":
        return [{"kind": "present"}]
    if kind == "unique":
        return [{"kind": "unique"}]
    if kind == "pattern":
        return [{"kind": "pattern", "value": constraint.pattern}]
    if kind == "gt":
        return [{"kind": "greater_than", "value": _literal_value(constraint.expression)}]
    if kind == "lt":
        return [{"kind": "less_than", "value": _literal_value(constraint.expression)}]
    if kind == "len_min":
        return [{"kind": "length_min", "value": _literal_value(constraint.expression)}]
    if kind == "len_max":
        return [{"kind": "length_max", "value": _literal_value(constraint.expression)}]
    return []


def _literal_value(expr: ir.Expression | None) -> object:
    if isinstance(expr, ir.Literal):
        return expr.value
    if expr is None:
        return None
    raise Namel3ssError("Manifest requires literal constraint values")


def _require_record(name: str, record_map: Dict[str, schema.RecordSchema], item: ir.PageItem) -> schema.RecordSchema:
    if name not in record_map:
        raise Namel3ssError(
            f"Page references unknown record '{name}'",
            line=item.line,
            column=item.column,
        )
    return record_map[name]


def _button_action_id(page_name: str, label: str) -> str:
    return f"page.{_slugify(page_name)}.button.{_slugify(label)}"


def _form_action_id(page_name: str, record_name: str) -> str:
    return f"page.{_slugify(page_name)}.form.{_slugify(record_name)}"


def _table_id(page_name: str, record_name: str) -> str:
    return f"page.{_slugify(page_name)}.table.{_slugify(record_name)}"


def _title_element_id(page_slug: str, index: int) -> str:
    return f"page.{page_slug}.title.{index}"


def _text_element_id(page_slug: str, index: int) -> str:
    return f"page.{page_slug}.text.{index}"


def _button_element_id(page_slug: str, index: int) -> str:
    return f"page.{page_slug}.button_item.{index}"


def _form_element_id(page_slug: str, index: int) -> str:
    return f"page.{page_slug}.form_item.{index}"


def _table_element_id(page_slug: str, index: int) -> str:
    return f"page.{page_slug}.table.{index}"


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed

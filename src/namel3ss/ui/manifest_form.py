from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.schema import records as schema
from namel3ss.ui.fields import field_to_ui


def _build_form_element(
    item: ir.FormItem,
    record: schema.RecordSchema,
    *,
    page_name: str,
    page_slug: str,
    element_id: str,
    action_id: str,
    index: int,
) -> tuple[dict, dict]:
    fields = [field_to_ui(field) for field in record.fields]
    if item.fields:
        overrides = {field.name: field for field in item.fields}
        for entry in fields:
            name = entry.get("name")
            config = overrides.get(name)
            if not config:
                continue
            if config.help is not None:
                entry["help"] = config.help
            if config.readonly:
                entry["readonly"] = True
    element = {
        "type": "form",
        "element_id": element_id,
        "id": action_id,
        "action_id": action_id,
        "record": record.name,
        "fields": fields,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }
    if item.groups:
        element["groups"] = [
            {"label": group.label, "fields": [ref.name for ref in group.fields]} for group in item.groups
        ]
    return element, {action_id: {"id": action_id, "type": "submit_form", "record": record.name}}


__all__ = ["_build_form_element"]

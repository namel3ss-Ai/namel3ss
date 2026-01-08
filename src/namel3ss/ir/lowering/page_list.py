from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import ListAction, ListItemMapping
from namel3ss.ir.lowering.page_actions import _validate_overlay_action
from namel3ss.schema import records as schema


def _lower_list_item_mapping(
    mapping: ast.ListItemMapping | None,
    record: schema.RecordSchema,
    variant: str,
    line: int,
    column: int,
) -> ListItemMapping:
    if mapping is None:
        primary = _default_list_primary(record)
        return ListItemMapping(primary=primary, secondary=None, meta=None, icon=None, line=line, column=column)
    for name in (mapping.primary, mapping.secondary, mapping.meta, mapping.icon):
        if not name:
            continue
        if name not in record.field_map:
            raise Namel3ssError(
                f"List item references unknown field '{name}' in record '{record.name}'",
                line=mapping.line,
                column=mapping.column,
            )
    if mapping.icon:
        if variant != "icon":
            raise Namel3ssError(
                "List icon requires variant 'icon'",
                line=mapping.line,
                column=mapping.column,
            )
        field = record.field_map.get(mapping.icon)
        text_types = {"text", "string", "str"}
        if field is None or field.type_name.lower() not in text_types:
            raise Namel3ssError(
                f"List icon field '{mapping.icon}' must be text",
                line=mapping.line,
                column=mapping.column,
            )
    return ListItemMapping(
        primary=mapping.primary,
        secondary=mapping.secondary,
        meta=mapping.meta,
        icon=mapping.icon,
        line=mapping.line,
        column=mapping.column,
    )


def _default_list_primary(record: schema.RecordSchema) -> str:
    text_types = {"text", "string", "str"}
    required_text = [
        field
        for field in record.fields
        if field.type_name.lower() in text_types and field.constraint and field.constraint.kind == "present"
    ]
    if required_text:
        return required_text[0].name
    text_fields = [field for field in record.fields if field.type_name.lower() in text_types]
    if text_fields:
        return text_fields[0].name
    return _list_id_field(record)


def _list_id_field(record: schema.RecordSchema) -> str:
    return "id" if "id" in record.field_map else "_id"


def _lower_list_actions(
    actions: list[ast.ListAction] | None,
    flow_names: set[str],
    page_name: str,
    overlays: dict[str, set[str]],
) -> list[ListAction] | None:
    if not actions:
        return None
    seen_labels: set[str] = set()
    lowered: list[ListAction] = []
    for action in actions:
        if action.kind == "call_flow":
            if action.flow_name not in flow_names:
                raise Namel3ssError(
                    f"Page '{page_name}' references unknown flow '{action.flow_name}'",
                    line=action.line,
                    column=action.column,
                )
        else:
            _validate_overlay_action(action, overlays, page_name)
        if action.label in seen_labels:
            raise Namel3ssError(
                f"List action label '{action.label}' is duplicated",
                line=action.line,
                column=action.column,
            )
        seen_labels.add(action.label)
        lowered.append(
            ListAction(
                label=action.label,
                flow_name=action.flow_name,
                kind=action.kind,
                target=action.target,
                line=action.line,
                column=action.column,
            )
        )
    return lowered


__all__ = [
    "_lower_list_item_mapping",
    "_lower_list_actions",
    "_default_list_primary",
    "_list_id_field",
]

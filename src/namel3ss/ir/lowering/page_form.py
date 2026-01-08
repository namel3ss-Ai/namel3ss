from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import FormFieldConfig, FormFieldRef, FormGroup
from namel3ss.schema import records as schema


def _lower_form_groups(
    groups: list[ast.FormGroup] | None,
    record: schema.RecordSchema,
    page_name: str,
) -> list[FormGroup] | None:
    if not groups:
        return None
    seen_fields: set[str] = set()
    lowered: list[FormGroup] = []
    for group in groups:
        field_refs: list[FormFieldRef] = []
        for ref in group.fields:
            name = ref.name
            if name not in record.field_map:
                raise Namel3ssError(
                    f"Form group references unknown field '{name}' in record '{record.name}'",
                    line=ref.line,
                    column=ref.column,
                )
            if name in seen_fields:
                raise Namel3ssError(
                    f"Form group references field '{name}' more than once",
                    line=ref.line,
                    column=ref.column,
                )
            seen_fields.add(name)
            field_refs.append(FormFieldRef(name=name, line=ref.line, column=ref.column))
        lowered.append(FormGroup(label=group.label, fields=field_refs, line=group.line, column=group.column))
    return lowered


def _lower_form_fields(
    fields: list[ast.FormFieldConfig] | None,
    record: schema.RecordSchema,
    page_name: str,
) -> list[FormFieldConfig] | None:
    if not fields:
        return None
    seen: set[str] = set()
    lowered: list[FormFieldConfig] = []
    for field in fields:
        name = field.name
        if name not in record.field_map:
            raise Namel3ssError(
                f"Form field '{name}' is not part of record '{record.name}'",
                line=field.line,
                column=field.column,
            )
        if name in seen:
            raise Namel3ssError(
                f"Form field '{name}' is configured more than once",
                line=field.line,
                column=field.column,
            )
        seen.add(name)
        lowered.append(
            FormFieldConfig(
                name=name,
                help=field.help,
                readonly=field.readonly,
                line=field.line,
                column=field.column,
            )
        )
    return lowered


__all__ = ["_lower_form_fields", "_lower_form_groups"]

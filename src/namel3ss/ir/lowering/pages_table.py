from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.page_actions import _validate_overlay_action
from namel3ss.ir.model.pages import TableColumnDirective, TablePagination, TableRowAction, TableSort
from namel3ss.schema import records as schema


def _lower_table_columns(
    columns: list[ast.TableColumnDirective] | None,
    record: schema.RecordSchema,
) -> list[TableColumnDirective] | None:
    if not columns:
        return None
    include_directives: dict[str, ast.TableColumnDirective] = {}
    exclude_directives: dict[str, ast.TableColumnDirective] = {}
    label_directives: dict[str, ast.TableColumnDirective] = {}
    for directive in columns:
        if directive.name not in record.field_map:
            raise Namel3ssError(
                f"Table references unknown field '{directive.name}' in record '{record.name}'",
                line=directive.line,
                column=directive.column,
            )
        if directive.kind == "include":
            if directive.name in include_directives:
                raise Namel3ssError(
                    f"Column '{directive.name}' is included more than once",
                    line=directive.line,
                    column=directive.column,
                )
            include_directives[directive.name] = directive
            continue
        if directive.kind == "exclude":
            if directive.name in exclude_directives:
                raise Namel3ssError(
                    f"Column '{directive.name}' is excluded more than once",
                    line=directive.line,
                    column=directive.column,
                )
            exclude_directives[directive.name] = directive
            continue
        if directive.kind == "label":
            if directive.name in label_directives:
                raise Namel3ssError(
                    f"Column '{directive.name}' label is declared more than once",
                    line=directive.line,
                    column=directive.column,
                )
            label_directives[directive.name] = directive
            continue
        raise Namel3ssError(
            f"Unsupported columns directive '{directive.kind}'",
            line=directive.line,
            column=directive.column,
        )
    overlap = set(include_directives) & set(exclude_directives)
    if overlap:
        name = sorted(overlap)[0]
        directive = include_directives.get(name) or exclude_directives.get(name)
        raise Namel3ssError(
            f"Column '{name}' cannot be both included and excluded",
            line=directive.line if directive else None,
            column=directive.column if directive else None,
        )
    if include_directives:
        for name, directive in label_directives.items():
            if name not in include_directives:
                raise Namel3ssError(
                    f"Column '{name}' is labeled but not included",
                    line=directive.line,
                    column=directive.column,
                )
    else:
        for name, directive in label_directives.items():
            if name in exclude_directives:
                raise Namel3ssError(
                    f"Column '{name}' is labeled but excluded",
                    line=directive.line,
                    column=directive.column,
                )
    return [
        TableColumnDirective(
            kind=directive.kind,
            name=directive.name,
            label=directive.label,
            line=directive.line,
            column=directive.column,
        )
        for directive in columns
    ]


def _lower_table_sort(sort: ast.TableSort | None, record: schema.RecordSchema) -> TableSort | None:
    if sort is None:
        return None
    field = record.field_map.get(sort.by)
    if field is None:
        raise Namel3ssError(
            f"Table sort references unknown field '{sort.by}' in record '{record.name}'",
            line=sort.line,
            column=sort.column,
        )
    comparable = {"text", "string", "str", "number", "int", "integer", "boolean", "bool"}
    if field.type_name.lower() not in comparable:
        raise Namel3ssError(
            f"Table sort field '{sort.by}' is not comparable",
            line=sort.line,
            column=sort.column,
        )
    return TableSort(by=sort.by, order=sort.order, line=sort.line, column=sort.column)


def _lower_table_pagination(pagination: ast.TablePagination | None) -> TablePagination | None:
    if pagination is None:
        return None
    return TablePagination(page_size=pagination.page_size, line=pagination.line, column=pagination.column)


def _lower_table_row_actions(
    actions: list[ast.TableRowAction] | None,
    flow_names: set[str],
    page_name: str,
    overlays: dict[str, set[str]],
) -> list[TableRowAction] | None:
    if not actions:
        return None
    seen_labels: set[str] = set()
    lowered: list[TableRowAction] = []
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
                f"Row action label '{action.label}' is duplicated",
                line=action.line,
                column=action.column,
            )
        seen_labels.add(action.label)
        lowered.append(
            TableRowAction(
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
    "_lower_table_columns",
    "_lower_table_sort",
    "_lower_table_pagination",
    "_lower_table_row_actions",
]

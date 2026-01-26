from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.page_chart import _lower_chart_item
from namel3ss.ir.lowering.page_chat import _lower_chat_item
from namel3ss.ir.lowering.page_form import _lower_form_fields, _lower_form_groups
from namel3ss.ir.lowering.page_list import _lower_list_actions, _lower_list_item_mapping
from namel3ss.ir.lowering.pages_table import (
    _lower_table_columns,
    _lower_table_pagination,
    _lower_table_row_actions,
    _lower_table_sort,
)
from namel3ss.ir.model.pages import (
    ChatItem,
    FormItem,
    ListItem,
    PageItem,
    TabItem,
    TabsItem,
    TableItem,
    UploadItem,
    ViewItem,
)
from namel3ss.schema import records as schema


def lower_view_item(
    item: ast.ViewItem,
    record_map: dict[str, schema.RecordSchema],
    *,
    attach_origin,
    unknown_record_message,
) -> ViewItem:
    if item.record_name not in record_map:
        raise Namel3ssError(
            unknown_record_message(item.record_name, record_map),
            line=item.line,
            column=item.column,
        )
    return attach_origin(ViewItem(record_name=item.record_name, line=item.line, column=item.column), item)


def lower_form_item(
    item: ast.FormItem,
    record_map: dict[str, schema.RecordSchema],
    page_name: str,
    *,
    attach_origin,
) -> FormItem:
    if item.record_name not in record_map:
        raise Namel3ssError(
            f"Page '{page_name}' references unknown record '{item.record_name}'",
            line=item.line,
            column=item.column,
        )
    record = record_map[item.record_name]
    groups = _lower_form_groups(item.groups, record, page_name)
    fields = _lower_form_fields(item.fields, record, page_name)
    return attach_origin(
        FormItem(
            record_name=item.record_name,
            groups=groups,
            fields=fields,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_upload_item(
    item: ast.UploadItem,
    *,
    attach_origin,
) -> UploadItem:
    accept = [entry.strip() for entry in (item.accept or []) if entry.strip()]
    multiple = bool(item.multiple) if item.multiple is not None else False
    return attach_origin(
        UploadItem(
            name=item.name,
            accept=accept,
            multiple=multiple,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_table_item(
    item: ast.TableItem,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    *,
    attach_origin,
) -> TableItem:
    if item.record_name not in record_map:
        raise Namel3ssError(
            f"Page '{page_name}' references unknown record '{item.record_name}'",
            line=item.line,
            column=item.column,
        )
    record = record_map[item.record_name]
    columns = _lower_table_columns(item.columns, record)
    sort = _lower_table_sort(item.sort, record)
    pagination = _lower_table_pagination(item.pagination)
    row_actions = _lower_table_row_actions(item.row_actions, flow_names, page_name, overlays)
    return attach_origin(
        TableItem(
            record_name=item.record_name,
            columns=columns,
            empty_text=item.empty_text,
            sort=sort,
            pagination=pagination,
            selection=item.selection,
            row_actions=row_actions,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_list_item(
    item: ast.ListItem,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    *,
    attach_origin,
) -> ListItem:
    if item.record_name not in record_map:
        raise Namel3ssError(
            f"Page '{page_name}' references unknown record '{item.record_name}'",
            line=item.line,
            column=item.column,
        )
    record = record_map[item.record_name]
    variant = item.variant or "two_line"
    mapping = _lower_list_item_mapping(item.item, record, variant, item.line, item.column)
    actions = _lower_list_actions(item.actions, flow_names, page_name, overlays)
    return attach_origin(
        ListItem(
            record_name=item.record_name,
            variant=variant,
            item=mapping,
            empty_text=item.empty_text,
            selection=item.selection,
            actions=actions,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_chart_item(
    item: ast.ChartItem,
    record_map: dict[str, schema.RecordSchema],
    page_name: str,
    *,
    attach_origin,
) -> PageItem:
    return attach_origin(_lower_chart_item(item, record_map, page_name), item)


def lower_chat_item(
    item: ast.ChatItem,
    flow_names: set[str],
    page_name: str,
    *,
    attach_origin,
) -> ChatItem:
    return attach_origin(_lower_chat_item(item, flow_names, page_name), item)


def lower_tabs_item(
    item: ast.TabsItem,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> TabsItem:
    lowered_tabs: list[TabItem] = []
    seen_labels: set[str] = set()
    for tab in item.tabs:
        if tab.label in seen_labels:
            raise Namel3ssError(
                f"Tab label '{tab.label}' is duplicated",
                line=tab.line,
                column=tab.column,
            )
        seen_labels.add(tab.label)
        children = [
            lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
            for child in tab.children
        ]
        lowered_tab = TabItem(label=tab.label, children=children, line=tab.line, column=tab.column)
        attach_origin(lowered_tab, tab)
        lowered_tabs.append(lowered_tab)
    if not lowered_tabs:
        raise Namel3ssError("Tabs block has no tabs", line=item.line, column=item.column)
    default_label = item.default or lowered_tabs[0].label
    if default_label not in seen_labels:
        raise Namel3ssError(
            f"Default tab '{default_label}' does not match any tab",
            line=item.line,
            column=item.column,
        )
    return attach_origin(
        TabsItem(
            tabs=lowered_tabs,
            default=default_label,
            line=item.line,
            column=item.column,
        ),
        item,
    )


__all__ = [
    "lower_chat_item",
    "lower_chart_item",
    "lower_form_item",
    "lower_list_item",
    "lower_table_item",
    "lower_tabs_item",
    "lower_upload_item",
    "lower_view_item",
]

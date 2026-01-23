from __future__ import annotations

from namel3ss.ui.consistency_models import (
    ActionSignature,
    ChartConfig,
    ColumnSignature,
    FormConfig,
    GroupSignature,
    ListConfig,
    ListMappingSignature,
    TableConfig,
    ViewConfig,
)
from namel3ss.ui.consistency_utils import _normalize_text, _string_or_none


def _table_config(element: dict) -> TableConfig:
    return TableConfig(
        columns=_table_columns_signature(element.get("columns")),
        sort=_table_sort_signature(element.get("sort")),
        pagination=_table_pagination_signature(element.get("pagination")),
        selection=_string_or_none(element.get("selection")),
        row_actions=_actions_signature(element.get("row_actions")),
    )


def _list_config(element: dict) -> ListConfig:
    return ListConfig(
        variant=_string_or_none(element.get("variant")),
        item=_list_item_signature(element.get("item")),
        selection=_string_or_none(element.get("selection")),
        actions=_actions_signature(element.get("actions")),
    )


def _form_config(element: dict) -> FormConfig:
    groups = _form_groups_signature(element.get("groups"))
    help_fields, readonly_fields = _form_field_flags(element.get("fields"))
    return FormConfig(groups=groups, help_fields=help_fields, readonly_fields=readonly_fields)


def _chart_config(element: dict, record: str, pairing: str | None) -> ChartConfig:
    source = _string_or_none(element.get("source"))
    if source is None:
        source = record
    return ChartConfig(
        chart_type=_string_or_none(element.get("chart_type")),
        x=_string_or_none(element.get("x")),
        y=_string_or_none(element.get("y")),
        source=source,
        paired_source=pairing,
    )


def _view_config(element: dict) -> ViewConfig:
    return ViewConfig(representation=_string_or_none(element.get("representation")))


def _table_columns_signature(columns: object) -> tuple[ColumnSignature, ...]:
    if not isinstance(columns, list):
        return ()
    signature: list[ColumnSignature] = []
    for entry in columns:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        label = entry.get("label")
        label_value = _normalize_text(label)
        signature.append((name, label_value))
    return tuple(signature)


def _table_sort_signature(sort: object) -> tuple[str, str] | None:
    if not isinstance(sort, dict):
        return None
    by = sort.get("by")
    order = sort.get("order")
    if isinstance(by, str) and isinstance(order, str):
        return (by, order)
    return None


def _table_pagination_signature(pagination: object) -> int | None:
    if not isinstance(pagination, dict):
        return None
    page_size = pagination.get("page_size")
    if isinstance(page_size, int):
        return page_size
    return None


def _actions_signature(actions: object) -> tuple[ActionSignature, ...]:
    if not isinstance(actions, list):
        return ()
    entries: list[ActionSignature] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        label = _normalize_text(action.get("label")) or ""
        if "flow" in action:
            flow = _string_or_none(action.get("flow"))
            entries.append((label, "call_flow", flow))
            continue
        kind = _string_or_none(action.get("type"))
        target = _string_or_none(action.get("target"))
        if kind:
            entries.append((label, kind, target))
    return tuple(entries)


def _list_item_signature(item: object) -> ListMappingSignature:
    if not isinstance(item, dict):
        return ()
    entries: list[tuple[str, str]] = []
    for key in ("primary", "secondary", "meta", "icon"):
        value = item.get(key)
        if isinstance(value, str) and value:
            entries.append((key, value))
    return tuple(entries)


def _form_groups_signature(groups: object) -> GroupSignature:
    if not isinstance(groups, list):
        return ()
    signature: list[tuple[str, tuple[str, ...]]] = []
    for entry in groups:
        if not isinstance(entry, dict):
            continue
        label = _normalize_text(entry.get("label")) or ""
        fields = entry.get("fields")
        field_names: list[str] = []
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, str) and field:
                    field_names.append(field)
        signature.append((label, tuple(field_names)))
    return tuple(signature)


def _form_field_flags(fields: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(fields, list):
        return (), ()
    help_fields: list[str] = []
    readonly_fields: list[str] = []
    for entry in fields:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        help_value = entry.get("help") if "help" in entry else None
        if isinstance(help_value, str) and help_value.strip():
            help_fields.append(name)
        if entry.get("readonly") is True:
            readonly_fields.append(name)
    return tuple(help_fields), tuple(readonly_fields)


__all__ = [
    "_actions_signature",
    "_chart_config",
    "_form_config",
    "_form_field_flags",
    "_form_groups_signature",
    "_list_config",
    "_list_item_signature",
    "_table_config",
    "_table_columns_signature",
    "_table_pagination_signature",
    "_table_sort_signature",
    "_view_config",
]

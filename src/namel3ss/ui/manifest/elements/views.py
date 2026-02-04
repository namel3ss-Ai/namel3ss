from __future__ import annotations

from typing import Dict, List

from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.page_list import _default_list_primary, _list_id_field as _list_id_field_ir
from namel3ss.runtime.records.service import build_record_scope
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.actions import _form_action_id
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest_chart import _build_chart_element, _resolve_state_list, _state_path_label
from namel3ss.ui.manifest_form import _build_form_element
from namel3ss.ui.manifest_list import (
    _build_list_actions,
    _list_id,
    _list_id_field,
    _list_item_mapping,
    _list_state_id,
)
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest_table import (
    _apply_table_pagination,
    _apply_table_sort,
    _build_row_actions,
    _resolve_state_table_columns,
    _resolve_table_columns,
    _table_id,
    _table_id_field,
    _table_state_id,
)
from namel3ss.validation import ValidationMode

from .base import _base_element, _require_record, _stable_rows_by_id, _view_representation
from .chat_views import build_chat_child_item, build_chat_item
from .tabs_views import build_tabs_item
from .upload_views import build_upload_item

# Default empty-state content for list/table when app does not specify empty_text.
# Keeps manifest deterministic and ensures empty collections render an empty state.
_DEFAULT_EMPTY_STATE_LIST = {"title": "No items", "text": "There are no items to display."}
_DEFAULT_EMPTY_STATE_TABLE = {"title": "No rows", "text": "There are no rows to display."}


def _empty_state_for_list(empty_text: str | None) -> dict:
    """Return deterministic empty_state dict for a list element."""
    if empty_text:
        return {"title": "No items", "text": empty_text}
    return dict(_DEFAULT_EMPTY_STATE_LIST)


def _empty_state_for_table(empty_text: str | None) -> dict:
    """Return deterministic empty_state dict for a table element."""
    if empty_text:
        return {"title": "No rows", "text": empty_text}
    return dict(_DEFAULT_EMPTY_STATE_TABLE)


def build_view_item(
    item: ir.ViewItem,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    record = _require_record(item.record_name, record_map, item)
    representation = _view_representation(record)
    element_id = _element_id(page_slug, "view", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    if representation == "table":
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        columns = _resolve_table_columns(record, None)
        rows = _stable_rows_by_id(rows, _table_id_field(record))
        element = {
            "type": "view",
            "representation": "table",
            "record": record.name,
            "id": _table_id(page_slug, record.name),
            "columns": columns,
            "rows": rows,
            **base,
        }
        element["id_field"] = _table_id_field(record)
        element["empty_state"] = _empty_state_for_table(None)
        return _attach_origin(element, item), {}
    rows = []
    if store is not None:
        scope = build_record_scope(record, identity)
        rows = store.list_records(record, scope=scope)[:20]
    primary = _default_list_primary(record)
    rows = _stable_rows_by_id(rows, _list_id_field_ir(record))
    element = {
        "type": "view",
        "representation": "list",
        "record": record.name,
        "id": _list_id(page_slug, record.name),
        "variant": "two_line",
        "item": {"primary": primary},
        "rows": rows,
        "empty_state": _empty_state_for_list(None),
        **base,
    }
    element["id_field"] = _list_id_field_ir(record)
    return _attach_origin(element, item), {}


def build_form_item(
    item: ir.FormItem,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    taken_actions: set[str],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    record = _require_record(item.record_name, record_map, item)
    element_id = _element_id(page_slug, "form_item", path)
    base_action_id = _form_action_id(page_slug, item.record_name)
    action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
    element, actions = _build_form_element(
        item,
        record,
        page_name=page_name,
        page_slug=page_slug,
        element_id=element_id,
        action_id=action_id,
        index=index,
    )
    return _attach_origin(element, item), actions


def build_table_item(
    item: ir.TableItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    *,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "table", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    if item.record_name:
        record = _require_record(item.record_name, record_map, item)
        table_id = _table_id(page_slug, item.record_name)
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        columns = _resolve_table_columns(record, item.columns)
        if item.sort:
            rows = _apply_table_sort(rows, item.sort, record)
        if item.pagination:
            rows = _apply_table_pagination(rows, item.pagination)
        row_actions, action_entries = _build_row_actions(
            element_id,
            page_slug,
            item.row_actions,
            state_ctx,
            mode,
            warnings,
        )
        element = {
            "type": "table",
            "id": table_id,
            "record": record.name,
            "columns": columns,
            "rows": rows,
            **base,
        }
        if item.empty_text:
            element["empty_text"] = item.empty_text
        if item.columns:
            element["columns_configured"] = True
        if item.sort:
            element["sort"] = {"by": item.sort.by, "order": item.sort.order}
        if item.pagination:
            element["pagination"] = {"page_size": item.pagination.page_size}
        if item.selection is not None:
            element["selection"] = item.selection
        if row_actions:
            element["row_actions"] = row_actions
        if row_actions or (item.selection in {"single", "multi"}):
            element["id_field"] = _table_id_field(record)
        return _attach_origin(element, item), action_entries
    source_label = _state_path_label(item.source)
    rows = _resolve_state_list(
        item.source,
        state_ctx,
        mode,
        warnings,
        item.line,
        item.column,
        label="Table source",
    )
    columns = _resolve_state_table_columns(item.columns or [])
    element = {
        "type": "table",
        "id": _table_state_id(page_slug, source_label),
        "source": source_label,
        "columns": columns,
        "rows": rows,
        "empty_state": _empty_state_for_table(item.empty_text),
        **base,
    }
    if item.empty_text:
        element["empty_text"] = item.empty_text
    element["columns_configured"] = True
    return _attach_origin(element, item), {}


def build_list_item(
    item: ir.ListItem,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "list", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    if item.record_name:
        record = _require_record(item.record_name, record_map, item)
        list_id = _list_id(page_slug, item.record_name)
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        action_entries, action_map = _build_list_actions(element_id, page_slug, item.actions, state_ctx, mode, warnings)
        element = {
            "type": "list",
            "id": list_id,
            "record": record.name,
            "variant": item.variant,
            "item": _list_item_mapping(item.item),
            "rows": rows,
            **base,
        }
        if item.empty_text:
            element["empty_text"] = item.empty_text
        if item.selection is not None:
            element["selection"] = item.selection
        if action_entries:
            element["actions"] = action_entries
        if action_entries or (item.selection in {"single", "multi"}):
            element["id_field"] = _list_id_field(record)
        return _attach_origin(element, item), action_map
    source_label = _state_path_label(item.source)
    rows = _resolve_state_list(
        item.source,
        state_ctx,
        mode,
        warnings,
        item.line,
        item.column,
        label="List source",
    )
    element = {
        "type": "list",
        "id": _list_state_id(page_slug, source_label),
        "source": source_label,
        "variant": item.variant,
        "item": _list_item_mapping(item.item),
        "rows": rows,
        "empty_state": _empty_state_for_list(item.empty_text),
        **base,
    }
    if item.empty_text:
        element["empty_text"] = item.empty_text
    return _attach_origin(element, item), {}


def build_chart_item(
    item: ir.ChartItem,
    record_map: Dict[str, schema.RecordSchema],
    *,
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    element_id = _element_id(page_slug, "chart", path)
    base = _base_element(element_id, page_name, page_slug, index, item)
    element = _build_chart_element(
        item,
        record_map,
        page_name=page_name,
        page_slug=page_slug,
        element_id=element_id,
        index=index,
        identity=identity,
        state_ctx=state_ctx,
        mode=mode,
        warnings=warnings,
        store=store,
    )
    return _attach_origin({**element, **base}, item), {}


__all__ = [
    "build_chart_item",
    "build_chat_child_item",
    "build_chat_item",
    "build_form_item",
    "build_list_item",
    "build_table_item",
    "build_tabs_item",
    "build_upload_item",
    "build_view_item",
]

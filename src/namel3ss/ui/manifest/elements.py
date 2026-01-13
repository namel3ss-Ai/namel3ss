from __future__ import annotations

from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.records.service import build_record_scope
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.actions import _allocate_action_id, _button_action_id, _form_action_id
from namel3ss.ui.manifest.canonical import _element_id
from namel3ss.ui.manifest.origin import _attach_origin
from namel3ss.ui.manifest_card import _build_card_actions, _build_card_stat
from namel3ss.ui.manifest_chart import _build_chart_element
from namel3ss.ui.manifest_chat import _chat_item_kind, _chat_item_to_manifest
from namel3ss.ui.manifest_form import _build_form_element
from namel3ss.ui.manifest_list import (
    _build_list_actions,
    _list_id,
    _list_id_field,
    _list_item_mapping,
)
from namel3ss.ui.manifest_overlay import _drawer_id, _modal_id
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.ui.manifest_table import (
    _apply_table_pagination,
    _apply_table_sort,
    _build_row_actions,
    _resolve_table_columns,
    _table_id,
    _table_id_field,
)
from namel3ss.validation import ValidationMode


def _base_element(element_id: str, page_name: str, page_slug: str, index: int, item: ir.PageItem) -> dict:
    return {
        "element_id": element_id,
        "page": page_name,
        "page_slug": page_slug,
        "index": index,
        "line": item.line,
        "column": item.column,
    }


def _build_children(
    children: List[ir.PageItem],
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    taken_actions: set[str],
) -> tuple[List[dict], Dict[str, dict]]:
    elements: List[dict] = []
    actions: Dict[str, dict] = {}
    for idx, child in enumerate(children):
        element, child_actions = _page_item_to_manifest(
            child,
            record_map,
            page_name,
            page_slug,
            path + [idx],
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        elements.append(element)
        for action_id, action_entry in child_actions.items():
            if action_id in actions:
                raise Namel3ssError(
                    f"Duplicate action id '{action_id}'. Use a unique id or omit to auto-generate.",
                    line=child.line,
                    column=child.column,
                )
            actions[action_id] = action_entry
            taken_actions.add(action_id)
    return elements, actions


def _page_item_to_manifest(
    item: ir.PageItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    taken_actions: set[str],
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    if isinstance(item, ir.TitleItem):
        element_id = _element_id(page_slug, "title", path)
        base = _base_element(element_id, page_name, page_slug, index, item)
        return (
            _attach_origin(
                {"type": "title", "value": item.value, **base},
                item,
            ),
            {},
        )
    if isinstance(item, ir.TextItem):
        element_id = _element_id(page_slug, "text", path)
        base = _base_element(element_id, page_name, page_slug, index, item)
        return (
            _attach_origin(
                {"type": "text", "value": item.value, **base},
                item,
            ),
            {},
        )
    if isinstance(item, ir.FormItem):
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
    if isinstance(item, ir.TableItem):
        record = _require_record(item.record_name, record_map, item)
        table_id = _table_id(page_slug, item.record_name)
        element_id = _element_id(page_slug, "table", path)
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        columns = _resolve_table_columns(record, item.columns)
        if item.sort:
            rows = _apply_table_sort(rows, item.sort, record)
        if item.pagination:
            rows = _apply_table_pagination(rows, item.pagination)
        row_actions, action_entries = _build_row_actions(element_id, page_slug, item.row_actions)
        base = _base_element(element_id, page_name, page_slug, index, item)
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
    if isinstance(item, ir.ListItem):
        record = _require_record(item.record_name, record_map, item)
        list_id = _list_id(page_slug, item.record_name)
        element_id = _element_id(page_slug, "list", path)
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        action_entries, action_map = _build_list_actions(element_id, item.actions)
        base = _base_element(element_id, page_name, page_slug, index, item)
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
    if isinstance(item, ir.ChartItem):
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
    if isinstance(item, ir.ChatItem):
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        element_id = _element_id(page_slug, "chat", path)
        base = _base_element(element_id, page_name, page_slug, index, item)
        element = {"type": "chat", "children": children, **base}
        return _attach_origin(element, item), actions
    chat_kind = _chat_item_kind(item)
    if chat_kind:
        element_id = _element_id(page_slug, chat_kind, path)
        result = _chat_item_to_manifest(
            item,
            element_id=element_id,
            page_name=page_name,
            page_slug=page_slug,
            index=index,
            state_ctx=state_ctx,
            mode=mode,
            warnings=warnings,
        )
        if result is not None:
            element, actions = result
            return _attach_origin(element, item), actions
    if isinstance(item, ir.ModalItem):
        element_id = _element_id(page_slug, "modal", path)
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(element_id, page_name, page_slug, index, item)
        element = {
            "type": "modal",
            "id": _modal_id(page_slug, item.label),
            "label": item.label,
            "open": False,
            "children": children,
            **base,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.DrawerItem):
        element_id = _element_id(page_slug, "drawer", path)
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(element_id, page_name, page_slug, index, item)
        element = {
            "type": "drawer",
            "id": _drawer_id(page_slug, item.label),
            "label": item.label,
            "open": False,
            "children": children,
            **base,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.TabsItem):
        element_id = _element_id(page_slug, "tabs", path)
        tabs: list[dict] = []
        action_map: Dict[str, dict] = {}
        labels: list[str] = []
        for idx, tab in enumerate(item.tabs):
            labels.append(tab.label)
            children, actions = _build_children(
                tab.children,
                record_map,
                page_name,
                page_slug,
                path + [idx],
                store,
                identity,
                state_ctx,
                mode,
                warnings,
                taken_actions,
            )
            action_map.update(actions)
            tab_base = _base_element(_element_id(page_slug, "tab", path + [idx]), page_name, page_slug, idx, tab)
            tabs.append(
                _attach_origin(
                    {
                        "type": "tab",
                        "label": tab.label,
                        "children": children,
                        **tab_base,
                    },
                    tab,
                )
            )
        default_label = item.default or (labels[0] if labels else "")
        base = _base_element(element_id, page_name, page_slug, index, item)
        element = {
            "type": "tabs",
            "tabs": labels,
            "default": default_label,
            "active": default_label,
            "children": tabs,
            **base,
        }
        return _attach_origin(element, item), action_map
    if isinstance(item, ir.ButtonItem):
        element_id = _element_id(page_slug, "button_item", path)
        base_action_id = _button_action_id(page_slug, item.label)
        action_id = _allocate_action_id(base_action_id, element_id, taken_actions)
        action_entry = {"id": action_id, "type": "call_flow", "flow": item.flow_name}
        base = _base_element(element_id, page_name, page_slug, index, item)
        element = {
            "type": "button",
            "label": item.label,
            "id": action_id,
            "action_id": action_id,
            "action": {"type": "call_flow", "flow": item.flow_name},
            **base,
        }
        return _attach_origin(element, item), {action_id: action_entry}
    if isinstance(item, ir.SectionItem):
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(_element_id(page_slug, "section", path), page_name, page_slug, index, item)
        element = {"type": "section", "label": item.label or "", "children": children, **base}
        return _attach_origin(element, item), actions
    if isinstance(item, ir.CardGroupItem):
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(_element_id(page_slug, "card_group", path), page_name, page_slug, index, item)
        element = {"type": "card_group", "children": children, **base}
        return _attach_origin(element, item), actions
    if isinstance(item, ir.CardItem):
        element_id = _element_id(page_slug, "card", path)
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(element_id, page_name, page_slug, index, item)
        element = {"type": "card", "label": item.label or "", "children": children, **base}
        if item.stat is not None:
            element["stat"] = _build_card_stat(item.stat, identity, state_ctx, mode, warnings)
        if item.actions:
            action_entries, action_map = _build_card_actions(element_id, page_slug, item.actions)
            element["actions"] = action_entries
            actions.update(action_map)
        return _attach_origin(element, item), actions
    if isinstance(item, ir.RowItem):
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(_element_id(page_slug, "row", path), page_name, page_slug, index, item)
        element = {"type": "row", "children": children, **base}
        return _attach_origin(element, item), actions
    if isinstance(item, ir.ColumnItem):
        children, actions = _build_children(
            item.children,
            record_map,
            page_name,
            page_slug,
            path,
            store,
            identity,
            state_ctx,
            mode,
            warnings,
            taken_actions,
        )
        base = _base_element(_element_id(page_slug, "column", path), page_name, page_slug, index, item)
        element = {"type": "column", "children": children, **base}
        return _attach_origin(element, item), actions
    if isinstance(item, ir.DividerItem):
        base = _base_element(_element_id(page_slug, "divider", path), page_name, page_slug, index, item)
        element = {"type": "divider", **base}
        return _attach_origin(element, item), {}
    if isinstance(item, ir.ImageItem):
        base = _base_element(_element_id(page_slug, "image", path), page_name, page_slug, index, item)
        element = {"type": "image", "src": item.src, "alt": item.alt, **base}
        return _attach_origin(element, item), {}
    raise Namel3ssError(
        f"Unsupported page item '{type(item)}'",
        line=getattr(item, "line", None),
        column=getattr(item, "column", None),
    )


def _require_record(name: str, record_map: Dict[str, schema.RecordSchema], item: ir.PageItem) -> schema.RecordSchema:
    if name not in record_map:
        raise Namel3ssError(
            f"Page references unknown record '{name}'. Add the record or update the reference.",
            line=item.line,
            column=item.column,
        )
    return record_map[name]


__all__ = ["_build_children"]

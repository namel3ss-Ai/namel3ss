from __future__ import annotations

from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.records.service import build_record_scope
from namel3ss.runtime.storage.base import Storage
from namel3ss.schema import records as schema
from namel3ss.ui.manifest.actions import _button_action_id, _form_action_id
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
from namel3ss.ui.manifest_table import (
    _apply_table_pagination,
    _apply_table_sort,
    _build_row_actions,
    _resolve_table_columns,
    _table_id,
    _table_id_field,
)


def _build_children(
    children: List[ir.PageItem],
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state: dict,
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
            state,
        )
        elements.append(element)
        for action_id, action_entry in child_actions.items():
            if action_id in actions:
                raise Namel3ssError(
                    f"UI action id '{action_id}' is duplicated on page '{page_name}'.",
                    line=child.line,
                    column=child.column,
                )
            actions[action_id] = action_entry
    return elements, actions


def _page_item_to_manifest(
    item: ir.PageItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
    state: dict,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    if isinstance(item, ir.TitleItem):
        element_id = _element_id(page_slug, "title", path)
        return (
            _attach_origin(
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
                item,
            ),
            {},
        )
    if isinstance(item, ir.TextItem):
        element_id = _element_id(page_slug, "text", path)
        return (
            _attach_origin(
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
                item,
            ),
            {},
        )
    if isinstance(item, ir.FormItem):
        record = _require_record(item.record_name, record_map, item)
        action_id = _form_action_id(page_name, item.record_name)
        element_id = _element_id(page_slug, "form_item", path)
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
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        columns = _resolve_table_columns(record, item.columns)
        if item.sort:
            rows = _apply_table_sort(rows, item.sort, record)
        if item.pagination:
            rows = _apply_table_pagination(rows, item.pagination)
        row_actions, action_entries = _build_row_actions(page_slug, record.name, item.row_actions)
        element = {
            "type": "table",
            "id": table_id,
            "record": record.name,
            "columns": columns,
            "rows": rows,
            "element_id": _element_id(page_slug, "table", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
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
        rows: list[dict] = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        action_entries, action_map = _build_list_actions(page_slug, record.name, item.actions)
        element = {
            "type": "list",
            "id": list_id,
            "record": record.name,
            "variant": item.variant,
            "item": _list_item_mapping(item.item),
            "rows": rows,
            "element_id": _element_id(page_slug, "list", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
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
        element = _build_chart_element(
            item,
            record_map,
            page_name=page_name,
            page_slug=page_slug,
            element_id=_element_id(page_slug, "chart", path),
            index=index,
            identity=identity,
            state=state,
            store=store,
        )
        return _attach_origin(element, item), {}
    if isinstance(item, ir.ChatItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "chat",
            "children": children,
            "element_id": _element_id(page_slug, "chat", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
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
            identity=identity,
            state=state,
        )
        if result is not None:
            element, actions = result
            return _attach_origin(element, item), actions
    if isinstance(item, ir.ModalItem):
        element_id = _element_id(page_slug, "modal", path)
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "modal",
            "id": _modal_id(page_slug, item.label),
            "label": item.label,
            "open": False,
            "children": children,
            "element_id": element_id,
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.DrawerItem):
        element_id = _element_id(page_slug, "drawer", path)
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "drawer",
            "id": _drawer_id(page_slug, item.label),
            "label": item.label,
            "open": False,
            "children": children,
            "element_id": element_id,
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
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
                tab.children, record_map, page_name, page_slug, path + [idx], store, identity, state
            )
            action_map.update(actions)
            tabs.append(
                _attach_origin(
                    {
                        "type": "tab",
                        "label": tab.label,
                        "children": children,
                        "element_id": _element_id(page_slug, "tab", path + [idx]),
                        "page": page_name,
                        "page_slug": page_slug,
                        "index": idx,
                        "line": tab.line,
                        "column": tab.column,
                    },
                    tab,
                )
            )
        default_label = item.default or (labels[0] if labels else "")
        element = {
            "type": "tabs",
            "tabs": labels,
            "default": default_label,
            "active": default_label,
            "children": tabs,
            "element_id": element_id,
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), action_map
    if isinstance(item, ir.ButtonItem):
        action_id = _button_action_id(page_name, item.label)
        action_entry = {"id": action_id, "type": "call_flow", "flow": item.flow_name}
        element_id = _element_id(page_slug, "button_item", path)
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
        return _attach_origin(element, item), {action_id: action_entry}
    if isinstance(item, ir.SectionItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "section",
            "label": item.label or "",
            "children": children,
            "element_id": _element_id(page_slug, "section", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.CardGroupItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "card_group",
            "children": children,
            "element_id": _element_id(page_slug, "card_group", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.CardItem):
        element_id = _element_id(page_slug, "card", path)
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "card",
            "label": item.label or "",
            "children": children,
            "element_id": element_id,
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        if item.stat is not None:
            element["stat"] = _build_card_stat(item.stat, identity, state)
        if item.actions:
            action_entries, action_map = _build_card_actions(element_id, page_slug, item.actions)
            element["actions"] = action_entries
            actions.update(action_map)
        return _attach_origin(element, item), actions
    if isinstance(item, ir.RowItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "row",
            "children": children,
            "element_id": _element_id(page_slug, "row", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.ColumnItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity, state
        )
        element = {
            "type": "column",
            "children": children,
            "element_id": _element_id(page_slug, "column", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), actions
    if isinstance(item, ir.DividerItem):
        element = {
            "type": "divider",
            "element_id": _element_id(page_slug, "divider", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return _attach_origin(element, item), {}
    if isinstance(item, ir.ImageItem):
        element = {
            "type": "image",
            "src": item.src,
            "alt": item.alt,
            "element_id": _element_id(page_slug, "image", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
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

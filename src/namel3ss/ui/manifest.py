from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.records.service import build_record_scope
from namel3ss.runtime.identity.guards import build_guard_context, enforce_requires
from namel3ss.runtime.storage.metadata import PersistenceMetadata
from namel3ss.runtime.theme.resolution import resolve_effective_theme, ThemeSource
from namel3ss.schema import records as schema
from namel3ss.ui.fields import field_to_ui


def build_manifest(
    program: ir.Program,
    *,
    state: dict | None = None,
    store: Storage | None = None,
    runtime_theme: str | None = None,
    persisted_theme: str | None = None,
    identity: dict | None = None,
) -> dict:
    ui_schema_version = "1"
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in program.records}
    pages = []
    actions: Dict[str, dict] = {}
    state = state or {}
    theme_setting = getattr(program, "theme", "system")
    theme_current = runtime_theme or theme_setting
    effective = resolve_effective_theme(theme_current, False, None)
    source = ThemeSource.APP.value
    if persisted_theme and persisted_theme == theme_current:
        source = ThemeSource.PERSISTED.value
    elif runtime_theme and runtime_theme != theme_setting:
        source = ThemeSource.SESSION.value
    identity = identity or {}
    for page in program.pages:
        enforce_requires(
            build_guard_context(identity=identity, state=state),
            getattr(page, "requires", None),
            subject=f'page "{page.name}"',
            line=page.line,
            column=page.column,
        )
        page_slug = _slugify(page.name)
        elements, action_entries = _build_children(
            page.items,
            record_map,
            page.name,
            page_slug,
            [],
            store,
            identity,
        )
        for action_id, action_entry in action_entries.items():
            actions[action_id] = action_entry
        pages.append(
            {
                "name": page.name,
                "slug": page_slug,
                "elements": elements,
            }
        )
    persistence = _resolve_persistence(store)
    return {
        "pages": pages,
        "actions": actions,
        "theme": {
            "schema_version": ui_schema_version,
            "setting": theme_setting,
            "current": theme_current,
            "persisted_current": persisted_theme,
            "effective": effective.value,
            "source": source,
            "runtime_supported": getattr(program, "theme_runtime_supported", False),
            "tokens": getattr(program, "theme_tokens", {}),
            "preference": getattr(program, "theme_preference", {"allow_override": False, "persist": "none"}),
        },
        "ui": {
            "persistence": persistence,
        },
    }


def _resolve_persistence(store: Storage | None) -> dict:
    default_meta = PersistenceMetadata(enabled=False, kind="memory", path=None, schema_version=None)
    if store is None:
        meta = default_meta
    else:
        getter = getattr(store, "get_metadata", None)
        meta = getter() if callable(getter) else default_meta
        meta = meta or default_meta
    if isinstance(meta, PersistenceMetadata):
        return asdict(meta)
    if isinstance(meta, dict):
        return {
            "enabled": bool(meta.get("enabled", False)),
            "kind": meta.get("kind") or "memory",
            "path": meta.get("path"),
            "schema_version": meta.get("schema_version"),
        }
    return asdict(default_meta)


def _build_children(
    children: List[ir.PageItem],
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
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
        )
        elements.append(element)
        actions.update(child_actions)
    return elements, actions


def _page_item_to_manifest(
    item: ir.PageItem,
    record_map: Dict[str, schema.RecordSchema],
    page_name: str,
    page_slug: str,
    path: List[int],
    store: Storage | None,
    identity: dict | None,
) -> tuple[dict, Dict[str, dict]]:
    index = path[-1] if path else 0
    if isinstance(item, ir.TitleItem):
        element_id = _element_id(page_slug, "title", path)
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
            {},
        )
    if isinstance(item, ir.TextItem):
        element_id = _element_id(page_slug, "text", path)
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
            {},
        )
    if isinstance(item, ir.FormItem):
        record = _require_record(item.record_name, record_map, item)
        action_id = _form_action_id(page_name, item.record_name)
        return (
            {
                "type": "form",
                "element_id": _element_id(page_slug, "form_item", path),
                "id": action_id,
                "action_id": action_id,
                "record": record.name,
                "fields": [field_to_ui(f) for f in record.fields],
                "page": page_name,
                "page_slug": page_slug,
                "index": index,
                "line": item.line,
                "column": item.column,
            },
            {action_id: {"id": action_id, "type": "submit_form", "record": record.name}},
        )
    if isinstance(item, ir.TableItem):
        record = _require_record(item.record_name, record_map, item)
        table_id = _table_id(page_name, item.record_name)
        rows = []
        if store is not None:
            scope = build_record_scope(record, identity)
            rows = store.list_records(record, scope=scope)[:20]
        return (
            {
                "type": "table",
                "id": table_id,
                "record": record.name,
                "columns": [{"name": f.name, "type": f.type_name} for f in record.fields],
                "rows": rows,
                "element_id": _element_id(page_slug, "table", path),
                "page": page_name,
                "page_slug": page_slug,
                "index": index,
                "line": item.line,
                "column": item.column,
            },
            {},
        )
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
        return element, {action_id: action_entry}
    if isinstance(item, ir.SectionItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity
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
        return element, actions
    if isinstance(item, ir.CardItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity
        )
        element = {
            "type": "card",
            "label": item.label or "",
            "children": children,
            "element_id": _element_id(page_slug, "card", path),
            "page": page_name,
            "page_slug": page_slug,
            "index": index,
            "line": item.line,
            "column": item.column,
        }
        return element, actions
    if isinstance(item, ir.RowItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity
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
        return element, actions
    if isinstance(item, ir.ColumnItem):
        children, actions = _build_children(
            item.children, record_map, page_name, page_slug, path, store, identity
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
        return element, actions
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
        return element, {}
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
        return element, {}
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


def _button_action_id(page_name: str, label: str) -> str:
    return f"page.{_slugify(page_name)}.button.{_slugify(label)}"


def _form_action_id(page_name: str, record_name: str) -> str:
    return f"page.{_slugify(page_name)}.form.{_slugify(record_name)}"


def _table_id(page_name: str, record_name: str) -> str:
    return f"page.{_slugify(page_name)}.table.{_slugify(record_name)}"


def _element_id(page_slug: str, kind: str, path: List[int]) -> str:
    suffix = ".".join(str(p) for p in path) if path else "0"
    return f"page.{page_slug}.{kind}.{suffix}"


def _slugify(text: str) -> str:
    import re

    lowered = text.lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    cleaned = re.sub(r"[^a-z0-9_]", "", normalized)
    collapsed = re.sub(r"_+", "_", cleaned).strip("_")
    return collapsed

from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.page_chart import _validate_chart_pairing
from namel3ss.ir.lowering.pages_items import _lower_page_item
from namel3ss.ir.lowering.ui_packs import expand_page_items
from namel3ss.ir.model.pages import Page
from namel3ss.schema import records as schema


def _lower_page(
    page: ast.PageDecl,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_names: set[str],
    pack_index: dict[str, ast.UIPackDecl],
) -> Page:
    expanded_items = expand_page_items(
        page.items,
        pack_index,
        allow_tabs=True,
        allow_overlays=True,
        columns_only=False,
        page_name=page.name,
    )
    overlays = _collect_overlays(expanded_items)
    _validate_upload_names(expanded_items)
    compose_names: set[str] = set()
    items = [
        _lower_page_item(item, record_map, flow_names, page.name, page_names, overlays, compose_names)
        for item in expanded_items
    ]
    _validate_chart_pairing(items, page.name)
    return Page(
        name=page.name,
        items=items,
        requires=_lower_expression(page.requires) if page.requires else None,
        purpose=getattr(page, "purpose", None),
        line=page.line,
        column=page.column,
        state_defaults=getattr(page, "state_defaults", None),
    )


def _collect_overlays(items: list[ast.PageItem]) -> dict[str, set[str]]:
    overlays: dict[str, dict[str, ast.PageItem]] = {"modal": {}, "drawer": {}}
    for item in items:
        if isinstance(item, ast.ModalItem):
            _register_overlay("modal", item.label, item, overlays)
        if isinstance(item, ast.DrawerItem):
            _register_overlay("drawer", item.label, item, overlays)
    return {kind: set(entries.keys()) for kind, entries in overlays.items()}


def _register_overlay(
    kind: str,
    label: str,
    item: ast.PageItem,
    overlays: dict[str, dict[str, ast.PageItem]],
) -> None:
    seen = overlays.get(kind)
    if seen is None:
        return
    if label in seen:
        dup = seen[label]
        raise Namel3ssError(
            f"{kind.capitalize()} '{label}' is duplicated",
            line=getattr(dup, "line", None),
            column=getattr(dup, "column", None),
        )
    seen[label] = item


def _validate_upload_names(items: list[ast.PageItem]) -> None:
    seen: dict[str, ast.UploadItem] = {}
    for item in _walk_page_items(items):
        if not isinstance(item, ast.UploadItem):
            continue
        if item.name in seen:
            raise Namel3ssError(
                f"Upload name '{item.name}' is duplicated",
                line=item.line,
                column=item.column,
            )
        seen[item.name] = item


def _walk_page_items(items: list[ast.PageItem]) -> list[ast.PageItem]:
    collected: list[ast.PageItem] = []
    for item in items:
        collected.append(item)
        if isinstance(item, ast.TabsItem):
            for tab in item.tabs:
                collected.extend(_walk_page_items(tab.children))
            continue
        if isinstance(
            item,
            (
                ast.CardGroupItem,
                ast.CardItem,
                ast.ChatItem,
                ast.ColumnItem,
                ast.ComposeItem,
                ast.DrawerItem,
                ast.ModalItem,
                ast.RowItem,
                ast.SectionItem,
            ),
        ):
            collected.extend(_walk_page_items(item.children))
    return collected


__all__ = ["_lower_page"]

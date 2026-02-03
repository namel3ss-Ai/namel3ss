from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.page_chart import _validate_chart_pairing
from namel3ss.ir.lowering.pages_items import _lower_page_item
from namel3ss.ir.lowering.ui_packs import expand_page_items
from namel3ss.ir.lowering.ui_patterns import expand_pattern_items
from namel3ss.ir.model.pages import Page, StatusBlock, StatusCase, StatusCondition
from namel3ss.schema import records as schema


def _lower_page(
    page: ast.PageDecl,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_names: set[str],
    pack_index: dict[str, ast.UIPackDecl],
    pattern_index: dict[str, object],
) -> Page:
    expanded_items = expand_page_items(
        page.items,
        pack_index,
        allow_tabs=True,
        allow_overlays=True,
        columns_only=False,
        page_name=page.name,
    )
    context_module = page.name.split(".", 1)[0] if "." in page.name else None
    expanded_items = expand_pattern_items(
        expanded_items,
        pattern_index,
        page_name=page.name,
        allow_tabs=True,
        allow_overlays=True,
        columns_only=False,
        flow_names=flow_names,
        page_names=page_names,
        record_names=set(record_map.keys()),
        context_module=context_module,
    )
    status_block, expanded_status_items = _lower_status_block(
        page,
        record_map,
        flow_names,
        page_names,
        pack_index,
        pattern_index,
        context_module,
    )
    overlays = _collect_overlays(expanded_items)
    _validate_upload_names(expanded_items, expanded_status_items)
    compose_names: set[str] = set()
    items = [
        _lower_page_item(item, record_map, flow_names, page.name, page_names, overlays, compose_names)
        for item in expanded_items
    ]
    status_items = _collect_lowered_status_items(status_block)
    _validate_chart_pairing(items + status_items, page.name)
    return Page(
        name=page.name,
        items=items,
        requires=_lower_expression(page.requires) if page.requires else None,
        purpose=getattr(page, "purpose", None),
        line=page.line,
        column=page.column,
        state_defaults=getattr(page, "state_defaults", None),
        status=status_block,
    )


def _lower_status_block(
    page: ast.PageDecl,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_names: set[str],
    pack_index: dict[str, ast.UIPackDecl],
    pattern_index: dict[str, object],
    context_module: str | None,
) -> tuple[StatusBlock | None, list[ast.PageItem]]:
    status = getattr(page, "status", None)
    if status is None:
        return None, []
    cases: list[StatusCase] = []
    expanded_status_items: list[ast.PageItem] = []
    for case in status.cases:
        expanded_items = expand_page_items(
            case.items,
            pack_index,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            page_name=page.name,
        )
        expanded_items = expand_pattern_items(
            expanded_items,
            pattern_index,
            page_name=page.name,
            allow_tabs=False,
            allow_overlays=False,
            columns_only=False,
            flow_names=flow_names,
            page_names=page_names,
            record_names=set(record_map.keys()),
            context_module=context_module,
        )
        expanded_status_items.extend(expanded_items)
        overlays = _collect_overlays(expanded_items)
        compose_names: set[str] = set()
        items = [
            _lower_page_item(item, record_map, flow_names, page.name, page_names, overlays, compose_names)
            for item in expanded_items
        ]
        condition = case.condition
        lowered_condition = StatusCondition(
            path=_lower_expression(condition.path),
            kind=condition.kind,
            value=_lower_expression(condition.value) if condition.value is not None else None,
            line=condition.line,
            column=condition.column,
        )
        cases.append(
            StatusCase(
                name=case.name,
                condition=lowered_condition,
                items=items,
                line=case.line,
                column=case.column,
            )
        )
    return StatusBlock(cases=cases, line=status.line, column=status.column), expanded_status_items


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


def _validate_upload_names(items: list[ast.PageItem], status_items: list[ast.PageItem]) -> None:
    seen: dict[str, ast.UploadItem] = {}
    for item in _walk_page_items(items + status_items):
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


def _collect_lowered_status_items(status_block: StatusBlock | None) -> list:
    if status_block is None:
        return []
    items: list[ast.PageItem] = []
    for case in status_block.cases:
        items.extend(case.items)
    return items


__all__ = ["_lower_page"]

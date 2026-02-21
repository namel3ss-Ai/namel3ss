from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.page_chart import _validate_chart_pairing
from namel3ss.ir.lowering.pages_items import _lower_page_item, set_plugin_registry
from namel3ss.ir.lowering.page_tokens import lower_page_theme_tokens
from namel3ss.ir.lowering.rag_ui_expand import expand_rag_ui_page
from namel3ss.ir.lowering.ui_navigation_expand import lower_navigation_sidebar
from namel3ss.ir.lowering.ui_packs import expand_page_items
from namel3ss.ir.lowering.ui_patterns import expand_pattern_items
from namel3ss.ir.model.base import Expression as IRExpression
from namel3ss.ir.model.expressions import Literal as IRLiteral
from namel3ss.ir.model.expressions import StatePath as IRStatePath
from namel3ss.ir.model.pages import (
    Page,
    PageLayout,
    StatusBlock,
    StatusCase,
    StatusCondition,
    VisibilityExpressionRule as IRVisibilityExpressionRule,
    VisibilityRule as IRVisibilityRule,
)
from namel3ss.schema import records as schema


def _lower_page(
    page: ast.PageDecl,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_names: set[str],
    pack_index: dict[str, ast.UIPackDecl],
    pattern_index: dict[str, object],
    plugin_registry,
    *,
    capabilities: tuple[str, ...] | None = None,
) -> Page:
    set_plugin_registry(plugin_registry)
    context_module = page.name.split(".", 1)[0] if "." in page.name else None
    rag_expansion = expand_rag_ui_page(page, capabilities=capabilities or ())
    rag_items = rag_expansion.items
    layout = getattr(page, "layout", None)
    expanded_layout: dict[str, list[ast.PageItem]] | None = None
    expanded_diagnostics_items: list[ast.PageItem] = []
    if layout is None:
        expanded_items = _expand_page_items(
            rag_items,
            page_name=page.name,
            flow_names=flow_names,
            page_names=page_names,
            record_names=set(record_map.keys()),
            context_module=context_module,
            pack_index=pack_index,
            pattern_index=pattern_index,
            allow_tabs=True,
            allow_overlays=True,
        )
    else:
        expanded_layout = {}
        expanded_items = []
        for slot_name in PAGE_LAYOUT_SLOT_ORDER:
            slot_items = getattr(layout, slot_name, None) or []
            expanded_slot_items = _expand_page_items(
                slot_items,
                page_name=page.name,
                flow_names=flow_names,
                page_names=page_names,
                record_names=set(record_map.keys()),
                context_module=context_module,
                pack_index=pack_index,
                pattern_index=pattern_index,
                allow_tabs=True,
                allow_overlays=True,
            )
            expanded_layout[slot_name] = expanded_slot_items
            expanded_items.extend(expanded_slot_items)
        diagnostics_items = getattr(layout, "diagnostics", None) or []
        expanded_diagnostics_items = _expand_page_items(
            diagnostics_items,
            page_name=page.name,
            flow_names=flow_names,
            page_names=page_names,
            record_names=set(record_map.keys()),
            context_module=context_module,
            pack_index=pack_index,
            pattern_index=pattern_index,
            allow_tabs=True,
            allow_overlays=True,
        )
        expanded_items.extend(expanded_diagnostics_items)
    status_block, expanded_status_items = _lower_status_block(
        page,
        record_map,
        flow_names,
        page_names,
        pack_index,
        pattern_index,
        context_module,
        plugin_registry,
    )
    overlays = _collect_overlays(expanded_items)
    _validate_upload_names(expanded_items, expanded_status_items)
    compose_names: set[str] = set()
    lowered_layout: PageLayout | None = None
    lowered_diagnostics_items: list = []
    if expanded_layout is None:
        items = [
            _lower_page_item(item, record_map, flow_names, page.name, page_names, overlays, compose_names)
            for item in expanded_items
        ]
    else:
        lowered_slot_items: dict[str, list] = {}
        for slot_name in PAGE_LAYOUT_SLOT_ORDER:
            lowered_items = [
                _lower_page_item(item, record_map, flow_names, page.name, page_names, overlays, compose_names)
                for item in expanded_layout.get(slot_name, [])
            ]
            lowered_slot_items[slot_name] = lowered_items
        items = _flatten_layout_slot_items(lowered_slot_items)
        lowered_diagnostics_items = [
            _lower_page_item(item, record_map, flow_names, page.name, page_names, overlays, compose_names)
            for item in expanded_diagnostics_items
        ]
        lowered_layout = PageLayout(
            header=lowered_slot_items["header"],
            sidebar_left=lowered_slot_items["sidebar_left"],
            main=lowered_slot_items["main"],
            drawer_right=lowered_slot_items["drawer_right"],
            footer=lowered_slot_items["footer"],
            diagnostics=lowered_diagnostics_items,
            sidebar_width=getattr(layout, "sidebar_width", None),
            drawer_width=getattr(layout, "drawer_width", None),
            panel_height=getattr(layout, "panel_height", None),
            resizable_panels=getattr(layout, "resizable_panels", None),
            line=layout.line,
            column=layout.column,
        )
        items.extend(lowered_diagnostics_items)
    status_items = _collect_lowered_status_items(status_block)
    _validate_chart_pairing(items + status_items, page.name)
    lowered_navigation = lower_navigation_sidebar(
        getattr(page, "ui_navigation", None),
        page_names,
        owner=f'Page "{page.name}"',
    )
    lowered_page = Page(
        name=page.name,
        items=items,
        layout=lowered_layout,
        requires=_lower_expression(page.requires) if page.requires else None,
        visibility=_lower_page_visibility(page),
        visibility_rule=_lower_page_visibility_rule(page),
        purpose=getattr(page, "purpose", None),
        debug_only=getattr(page, "debug_only", None),
        diagnostics=getattr(page, "diagnostics", None),
        line=page.line,
        column=page.column,
        state_defaults=getattr(page, "state_defaults", None),
        status=status_block,
        theme_tokens=lower_page_theme_tokens(getattr(page, "theme_tokens", None)),
        ui_theme_overrides=lower_page_theme_tokens(rag_expansion.theme_overrides),
    )
    if lowered_navigation is not None:
        setattr(lowered_page, "ui_navigation", lowered_navigation)
    return lowered_page


def _expand_page_items(
    items: list[ast.PageItem],
    *,
    page_name: str,
    flow_names: set[str],
    page_names: set[str],
    record_names: set[str],
    context_module: str | None,
    pack_index: dict[str, ast.UIPackDecl],
    pattern_index: dict[str, object],
    allow_tabs: bool,
    allow_overlays: bool,
) -> list[ast.PageItem]:
    expanded_items = expand_page_items(
        items,
        pack_index,
        allow_tabs=allow_tabs,
        allow_overlays=allow_overlays,
        columns_only=False,
        page_name=page_name,
    )
    return expand_pattern_items(
        expanded_items,
        pattern_index,
        page_name=page_name,
        allow_tabs=allow_tabs,
        allow_overlays=allow_overlays,
        columns_only=False,
        flow_names=flow_names,
        page_names=page_names,
        record_names=record_names,
        context_module=context_module,
    )


def _flatten_layout_slot_items(slot_items: dict[str, list]) -> list:
    items: list = []
    for slot_name in PAGE_LAYOUT_SLOT_ORDER:
        values = slot_items.get(slot_name)
        if isinstance(values, list):
            items.extend(values)
    return items


def _lower_status_block(
    page: ast.PageDecl,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_names: set[str],
    pack_index: dict[str, ast.UIPackDecl],
    pattern_index: dict[str, object],
    context_module: str | None,
    plugin_registry,
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
        if isinstance(item, ast.ConditionalBlock):
            collected.extend(_walk_page_items(item.then_children))
            if item.else_children:
                collected.extend(_walk_page_items(item.else_children))
            continue
        if isinstance(item, ast.SidebarLayout):
            collected.extend(_walk_page_items(item.sidebar))
            collected.extend(_walk_page_items(item.main))
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
                ast.GridItem,
                ast.LayoutColumn,
                ast.LayoutDrawer,
                ast.LayoutGrid,
                ast.LayoutRow,
                ast.LayoutStack,
                ast.LayoutSticky,
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


def _lower_page_visibility(page: ast.PageDecl) -> IRExpression | None:
    visibility = getattr(page, "visibility", None)
    if visibility is None:
        return None
    if isinstance(visibility, ast.PatternParamRef):
        raise Namel3ssError(
            "Visibility expressions cannot use unresolved pattern parameters.",
            line=getattr(page, "line", None),
            column=getattr(page, "column", None),
        )
    lowered = _lower_expression(visibility)
    if not isinstance(lowered, IRExpression):
        raise Namel3ssError(
            "Visibility requires a deterministic expression.",
            line=getattr(page, "line", None),
            column=getattr(page, "column", None),
        )
    return lowered


def _lower_page_visibility_rule(page: ast.PageDecl) -> IRVisibilityRule | IRVisibilityExpressionRule | None:
    rule = getattr(page, "visibility_rule", None)
    if rule is None:
        return None
    if isinstance(rule, ast.VisibilityExpressionRule):
        lowered_expr = _lower_expression(rule.expression)
        if not isinstance(lowered_expr, IRExpression):
            raise Namel3ssError(
                "Visibility expressions require deterministic operands.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        return IRVisibilityExpressionRule(expression=lowered_expr, line=rule.line, column=rule.column)
    if isinstance(rule, ast.VisibilityRule):
        lowered_path = _lower_expression(rule.path)
        if not isinstance(lowered_path, IRStatePath):
            raise Namel3ssError(
                "Visibility rule requires state.<path> is <value>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        lowered_value = _lower_expression(rule.value)
        if not isinstance(lowered_value, IRLiteral):
            raise Namel3ssError(
                "Visibility rule requires a text, number, or boolean literal.",
                line=getattr(rule.value, "line", None),
                column=getattr(rule.value, "column", None),
            )
        return IRVisibilityRule(path=lowered_path, value=lowered_value, line=rule.line, column=rule.column)
    raise Namel3ssError(
        "Visibility rule requires either an expression or state.<path> is <value>.",
        line=getattr(page, "line", None),
        column=getattr(page, "column", None),
    )


__all__ = ["_lower_page"]

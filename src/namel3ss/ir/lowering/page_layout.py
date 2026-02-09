from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model.base import Expression as IRExpression
from namel3ss.ir.model.ui_layout import (
    ConditionalBlock,
    LayoutColumn,
    LayoutDrawer,
    LayoutGrid,
    LayoutRow,
    LayoutStack,
    LayoutSticky,
    SidebarLayout,
)


def lower_layout_item(
    item: ast.PageItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
):
    if isinstance(item, ast.LayoutStack):
        children = _lower_children(
            item.children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(
            LayoutStack(children=children, direction=item.direction, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.LayoutRow):
        children = _lower_children(
            item.children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(LayoutRow(children=children, line=item.line, column=item.column), item)
    if isinstance(item, ast.LayoutColumn):
        children = _lower_children(
            item.children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(LayoutColumn(children=children, line=item.line, column=item.column), item)
    if isinstance(item, ast.LayoutGrid):
        children = _lower_children(
            item.children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(
            LayoutGrid(columns=int(item.columns), children=children, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.SidebarLayout):
        sidebar = _lower_children(
            item.sidebar,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        main = _lower_children(
            item.main,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(
            SidebarLayout(sidebar=sidebar, main=main, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.LayoutDrawer):
        title = item.title
        if isinstance(title, ast.PatternParamRef):
            raise Namel3ssError(
                "Drawer title cannot use unresolved pattern parameters.",
                line=getattr(item, "line", None),
                column=getattr(item, "column", None),
            )
        children = _lower_children(
            item.children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(
            LayoutDrawer(title=str(title), children=children, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.LayoutSticky):
        children = _lower_children(
            item.children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        return attach_origin(
            LayoutSticky(position=item.position, children=children, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.ConditionalBlock):
        lowered_condition = _lower_condition(item.condition, item)
        then_children = _lower_children(
            item.then_children,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
            lower_page_item,
        )
        else_children = None
        if item.else_children is not None:
            else_children = _lower_children(
                item.else_children,
                record_map,
                flow_names,
                page_name,
                page_names,
                overlays,
                compose_names,
                lower_page_item,
            )
        return attach_origin(
            ConditionalBlock(
                condition=lowered_condition,
                then_children=then_children,
                else_children=else_children,
                line=item.line,
                column=item.column,
            ),
            item,
        )
    return None


def _lower_children(
    children: list[ast.PageItem],
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    lower_page_item,
) -> list:
    return [
        lower_page_item(
            child,
            record_map,
            flow_names,
            page_name,
            page_names,
            overlays,
            compose_names,
        )
        for child in children
    ]


def _lower_condition(expr: ast.Expression | ast.PatternParamRef, item: ast.PageItem) -> IRExpression:
    if isinstance(expr, ast.PatternParamRef):
        raise Namel3ssError(
            "Conditional expressions cannot use unresolved pattern parameters.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )
    lowered = _lower_expression(expr)
    if not isinstance(lowered, IRExpression):
        raise Namel3ssError(
            "Conditional expressions require deterministic operands.",
            line=getattr(item, "line", None),
            column=getattr(item, "column", None),
        )
    return lowered


__all__ = ["lower_layout_item"]

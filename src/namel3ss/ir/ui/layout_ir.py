from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

from namel3ss.ast.ui import layout_nodes as ast
from namel3ss.ir.ui.layout_ir_model import (
    ActionIR,
    CardIR,
    DrawerIR,
    FormIR,
    InteractionBindingIR,
    LayoutElementIR,
    LiteralItemIR,
    MainIR,
    MediaIR,
    NavigationTabsIR,
    PageLayoutIR,
    ScrollAreaIR,
    SidebarIR,
    StickyIR,
    TableIR,
    ThreePaneIR,
    TwoPaneIR,
    slugify_layout_name,
    stable_layout_id,
)


@dataclass
class _LoweringContext:
    page_slug: str
    actions: list[ActionIR] = field(default_factory=list)


def lower_layout_page(page: ast.PageNode) -> PageLayoutIR:
    page_slug = slugify_layout_name(page.name)
    context = _LoweringContext(page_slug=page_slug)
    elements: list[LayoutElementIR] = []
    for index, node in enumerate(page.children):
        elements.append(_lower_node(node, path=(index,), page_name=page.name, ctx=context))
    actions = sorted(context.actions, key=_action_sort_key)
    return PageLayoutIR(
        name=page.name,
        state_paths=[entry.path for entry in page.states],
        elements=elements,
        actions=actions,
    )


def _lower_node(
    node: ast.LayoutNode,
    *,
    path: tuple[int, ...],
    page_name: str,
    ctx: _LoweringContext,
) -> LayoutElementIR:
    if isinstance(node, ast.LiteralItemNode):
        element_id = stable_layout_id(page_name, "literal", line=node.line, column=node.column, path=path)
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return LiteralItemIR(id=element_id, text=node.text, bindings=bindings, line=node.line, column=node.column)
    if isinstance(node, ast.FormNode):
        element_id = stable_layout_id(page_name, "form", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return FormIR(
            id=element_id,
            name=node.name,
            wizard=node.wizard,
            sections=list(node.sections),
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.TableNode):
        element_id = stable_layout_id(page_name, "table", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return TableIR(
            id=element_id,
            name=node.name,
            reorderable_columns=node.reorderable_columns,
            fixed_header=node.fixed_header,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.CardNode):
        element_id = stable_layout_id(page_name, "card", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return CardIR(
            id=element_id,
            name=node.name,
            expandable=node.expandable,
            collapsed=node.collapsed,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.NavigationTabsNode):
        element_id = stable_layout_id(page_name, "tabs", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return NavigationTabsIR(
            id=element_id,
            name=node.name,
            dynamic_from_state=node.dynamic_from_state,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.MediaNode):
        element_id = stable_layout_id(page_name, "media", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return MediaIR(
            id=element_id,
            name=node.name,
            inline_crop=node.inline_crop,
            annotation=node.annotation,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.SidebarNode):
        element_id = stable_layout_id(page_name, "sidebar", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return SidebarIR(id=element_id, children=children, bindings=bindings, line=node.line, column=node.column)
    if isinstance(node, ast.MainNode):
        element_id = stable_layout_id(page_name, "main", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return MainIR(id=element_id, children=children, bindings=bindings, line=node.line, column=node.column)
    if isinstance(node, ast.DrawerNode):
        element_id = stable_layout_id(page_name, "drawer", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return DrawerIR(
            id=element_id,
            side=node.side,
            trigger_id=node.trigger_id,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.StickyNode):
        element_id = stable_layout_id(page_name, "sticky", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return StickyIR(
            id=element_id,
            position=node.position,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.ScrollAreaNode):
        element_id = stable_layout_id(page_name, "scroll_area", line=node.line, column=node.column, path=path)
        children = [_lower_node(child, path=path + (index,), page_name=page_name, ctx=ctx) for index, child in enumerate(node.children)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return ScrollAreaIR(
            id=element_id,
            axis=node.axis,
            children=children,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.TwoPaneNode):
        element_id = stable_layout_id(page_name, "two_pane", line=node.line, column=node.column, path=path)
        primary = [_lower_node(child, path=path + (0, index), page_name=page_name, ctx=ctx) for index, child in enumerate(node.primary)]
        secondary = [_lower_node(child, path=path + (1, index), page_name=page_name, ctx=ctx) for index, child in enumerate(node.secondary)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return TwoPaneIR(
            id=element_id,
            primary=primary,
            secondary=secondary,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    if isinstance(node, ast.ThreePaneNode):
        element_id = stable_layout_id(page_name, "three_pane", line=node.line, column=node.column, path=path)
        left = [_lower_node(child, path=path + (0, index), page_name=page_name, ctx=ctx) for index, child in enumerate(node.left)]
        center = [_lower_node(child, path=path + (1, index), page_name=page_name, ctx=ctx) for index, child in enumerate(node.center)]
        right = [_lower_node(child, path=path + (2, index), page_name=page_name, ctx=ctx) for index, child in enumerate(node.right)]
        bindings = _lower_bindings(node.bindings, node_id=element_id, line=node.line, column=node.column, ctx=ctx)
        return ThreePaneIR(
            id=element_id,
            left=left,
            center=center,
            right=right,
            bindings=bindings,
            line=node.line,
            column=node.column,
        )
    raise TypeError(f"Unsupported layout node type: {type(node)!r}")


def _lower_bindings(
    bindings: ast.InteractionBindings,
    *,
    node_id: str,
    line: int | None,
    column: int | None,
    ctx: _LoweringContext,
) -> InteractionBindingIR:
    if bindings.on_click:
        action_id = _stable_action_id(
            page_slug=ctx.page_slug,
            event="click",
            node_id=node_id,
            target=bindings.on_click,
            ordinal=len(ctx.actions),
        )
        ctx.actions.append(
            ActionIR(
                id=action_id,
                event="click",
                node_id=node_id,
                target=bindings.on_click,
                line=line,
                column=column,
            )
        )
    if bindings.keyboard_shortcut:
        action_id = _stable_action_id(
            page_slug=ctx.page_slug,
            event="keyboard_shortcut",
            node_id=node_id,
            target=bindings.keyboard_shortcut,
            ordinal=len(ctx.actions),
        )
        ctx.actions.append(
            ActionIR(
                id=action_id,
                event="keyboard_shortcut",
                node_id=node_id,
                target=bindings.keyboard_shortcut,
                line=line,
                column=column,
            )
        )
    return InteractionBindingIR(
        on_click=bindings.on_click,
        keyboard_shortcut=bindings.keyboard_shortcut,
        selected_item=bindings.selected_item,
    )


def _stable_action_id(
    *,
    page_slug: str,
    event: str,
    node_id: str,
    target: str,
    ordinal: int,
) -> str:
    payload = f"{page_slug}|{event}|{node_id}|{target}|{ordinal}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"action.{page_slug}.{event}.{digest}"


def _action_sort_key(action: ActionIR) -> tuple[int, int, str, str, str]:
    return (
        action.line or 0,
        action.column or 0,
        action.event,
        action.target,
        action.node_id,
    )


__all__ = [
    "ActionIR",
    "CardIR",
    "DrawerIR",
    "FormIR",
    "InteractionBindingIR",
    "LayoutElementIR",
    "LiteralItemIR",
    "MainIR",
    "MediaIR",
    "NavigationTabsIR",
    "PageLayoutIR",
    "ScrollAreaIR",
    "SidebarIR",
    "StickyIR",
    "TableIR",
    "ThreePaneIR",
    "TwoPaneIR",
    "lower_layout_page",
    "stable_layout_id",
]

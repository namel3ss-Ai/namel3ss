from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.flow_refs import unknown_flow_message
from namel3ss.ir.lowering.page_actions import _validate_overlay_action
from namel3ss.ir.model.pages import (
    ActionAvailabilityRule,
    ButtonItem,
    CardAction,
    CardGroupItem,
    CardItem,
    CardStat,
    ColumnItem,
    ComposeItem,
    DividerItem,
    DrawerItem,
    LinkItem,
    ModalItem,
    PageItem,
    RowItem,
    SectionItem,
    TextItem,
    TextInputItem,
    TitleItem,
)


def lower_compose_item(
    item: ast.ComposeItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> ComposeItem:
    if item.name in compose_names:
        raise Namel3ssError(
            f"Compose name '{item.name}' is duplicated",
            line=item.line,
            column=item.column,
        )
    compose_names.add(item.name)
    children = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    return attach_origin(ComposeItem(name=item.name, children=children, line=item.line, column=item.column), item)


def lower_title_item(item: ast.TitleItem, *, attach_origin) -> TitleItem:
    return attach_origin(TitleItem(value=item.value, line=item.line, column=item.column), item)


def lower_text_item(item: ast.TextItem, *, attach_origin) -> TextItem:
    return attach_origin(TextItem(value=item.value, line=item.line, column=item.column), item)


def lower_text_input_item(
    item: ast.TextInputItem,
    flow_names: set[str],
    page_name: str,
    *,
    attach_origin,
) -> TextInputItem:
    if item.flow_name not in flow_names:
        raise Namel3ssError(
            unknown_flow_message(item.flow_name, flow_names, page_name),
            line=item.line,
            column=item.column,
        )
    availability_rule = _lower_action_availability_rule(getattr(item, "availability_rule", None))
    return attach_origin(
        TextInputItem(
            name=item.name,
            flow_name=item.flow_name,
            availability_rule=availability_rule,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_button_item(
    item: ast.ButtonItem,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    *,
    attach_origin,
) -> ButtonItem:
    action_kind = str(getattr(item, "action_kind", "call_flow") or "call_flow")
    target = getattr(item, "target", None)
    if action_kind == "call_flow":
        if item.flow_name not in flow_names:
            raise Namel3ssError(
                unknown_flow_message(item.flow_name, flow_names, page_name),
                line=item.line,
                column=item.column,
            )
    elif action_kind == "navigate_to":
        if target not in page_names:
            raise Namel3ssError(
                f"Page '{page_name}' button '{item.label}' references unknown page '{target}'",
                line=item.line,
                column=item.column,
            )
    elif action_kind != "go_back":
        raise Namel3ssError(
            f"Unsupported button action '{action_kind}'",
            line=item.line,
            column=item.column,
        )
    availability_rule = _lower_action_availability_rule(getattr(item, "availability_rule", None))
    return attach_origin(
        ButtonItem(
            label=item.label,
            flow_name=item.flow_name,
            action_kind=action_kind,
            target=target,
            icon=getattr(item, "icon", None),
            availability_rule=availability_rule,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_link_item(
    item: ast.LinkItem,
    page_names: set[str],
    *,
    attach_origin,
    unknown_page_message,
) -> LinkItem:
    if item.page_name not in page_names:
        raise Namel3ssError(
            unknown_page_message(item.page_name, page_names),
            line=item.line,
            column=item.column,
        )
    return attach_origin(
        LinkItem(label=item.label, page_name=item.page_name, line=item.line, column=item.column),
        item,
    )


def lower_section_item(
    item: ast.SectionItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> SectionItem:
    children = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    return attach_origin(
        SectionItem(
            label=item.label,
            children=children,
            columns=list(getattr(item, "columns", []) or []) or None,
            line=item.line,
            column=item.column,
        ),
        item,
    )


def lower_card_group_item(
    item: ast.CardGroupItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> CardGroupItem:
    lowered_children: list[PageItem] = []
    for child in item.children:
        if not isinstance(child, ast.CardItem):
            raise Namel3ssError("Card groups may only contain cards", line=child.line, column=child.column)
        lowered_children.append(
            lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        )
    return attach_origin(CardGroupItem(children=lowered_children, line=item.line, column=item.column), item)


def lower_card_item(
    item: ast.CardItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> CardItem:
    children = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    stat = _lower_card_stat(item.stat)
    actions = _lower_card_actions(item.actions, flow_names, page_name, page_names, overlays)
    return attach_origin(
        CardItem(label=item.label, children=children, stat=stat, actions=actions, line=item.line, column=item.column),
        item,
    )


def lower_row_item(
    item: ast.RowItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> RowItem:
    lowered_children: list[PageItem] = []
    for child in item.children:
        if not isinstance(child, ast.ColumnItem):
            raise Namel3ssError("Rows may only contain columns", line=child.line, column=child.column)
        lowered_children.append(
            lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        )
    return attach_origin(RowItem(children=lowered_children, line=item.line, column=item.column), item)


def lower_column_item(
    item: ast.ColumnItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> ColumnItem:
    children = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    return attach_origin(ColumnItem(children=children, line=item.line, column=item.column), item)


def lower_divider_item(item: ast.DividerItem, *, attach_origin) -> DividerItem:
    return attach_origin(DividerItem(line=item.line, column=item.column), item)


def lower_modal_item(
    item: ast.ModalItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> ModalItem:
    children = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    return attach_origin(ModalItem(label=item.label, children=children, line=item.line, column=item.column), item)


def lower_drawer_item(
    item: ast.DrawerItem,
    record_map,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
    compose_names: set[str],
    *,
    lower_page_item,
    attach_origin,
) -> DrawerItem:
    children = [
        lower_page_item(child, record_map, flow_names, page_name, page_names, overlays, compose_names)
        for child in item.children
    ]
    return attach_origin(DrawerItem(label=item.label, children=children, line=item.line, column=item.column), item)


def _lower_card_actions(
    actions: list[ast.CardAction] | None,
    flow_names: set[str],
    page_name: str,
    page_names: set[str],
    overlays: dict[str, set[str]],
) -> list[CardAction] | None:
    if not actions:
        return None
    seen_labels: set[str] = set()
    lowered: list[CardAction] = []
    for action in actions:
        if action.kind == "call_flow":
            if action.flow_name not in flow_names:
                raise Namel3ssError(
                    unknown_flow_message(action.flow_name, flow_names, page_name),
                    line=action.line,
                    column=action.column,
                )
        else:
            _validate_overlay_action(action, overlays, page_name, page_names)
        if action.label in seen_labels:
            raise Namel3ssError(
                f"Card action label '{action.label}' is duplicated",
                line=action.line,
                column=action.column,
            )
        seen_labels.add(action.label)
        availability_rule = _lower_action_availability_rule(getattr(action, "availability_rule", None))
        lowered.append(
            CardAction(
                label=action.label,
                flow_name=action.flow_name,
                kind=action.kind,
                target=action.target,
                availability_rule=availability_rule,
                line=action.line,
                column=action.column,
            )
        )
    return lowered


def _lower_card_stat(stat: ast.CardStat | None) -> CardStat | None:
    if stat is None:
        return None
    _reject_card_stat_calls(stat.value)
    return CardStat(
        value=_lower_expression(stat.value),
        label=stat.label,
        line=stat.line,
        column=stat.column,
    )


def _lower_action_availability_rule(rule: ast.ActionAvailabilityRule | None) -> ActionAvailabilityRule | None:
    if rule is None:
        return None
    return ActionAvailabilityRule(
        path=_lower_expression(rule.path),
        value=_lower_expression(rule.value),
        line=rule.line,
        column=rule.column,
    )


def _reject_card_stat_calls(expr: ast.Expression) -> None:
    if isinstance(expr, ast.ToolCallExpr):
        raise Namel3ssError(
            "Card stat expressions cannot call tools",
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.CallFunctionExpr):
        raise Namel3ssError(
            "Card stat expressions cannot call functions",
            line=expr.line,
            column=expr.column,
        )
    if isinstance(expr, ast.UnaryOp):
        _reject_card_stat_calls(expr.operand)
        return
    if isinstance(expr, ast.BinaryOp):
        _reject_card_stat_calls(expr.left)
        _reject_card_stat_calls(expr.right)
        return
    if isinstance(expr, ast.Comparison):
        _reject_card_stat_calls(expr.left)
        _reject_card_stat_calls(expr.right)
        return
    if isinstance(expr, ast.ListExpr):
        for item in expr.items:
            _reject_card_stat_calls(item)
        return
    if isinstance(expr, ast.MapExpr):
        for entry in expr.entries:
            _reject_card_stat_calls(entry.key)
            _reject_card_stat_calls(entry.value)
        return
    if isinstance(expr, ast.ListOpExpr):
        _reject_card_stat_calls(expr.target)
        if expr.value is not None:
            _reject_card_stat_calls(expr.value)
        if expr.index is not None:
            _reject_card_stat_calls(expr.index)
        return
    if isinstance(expr, ast.MapOpExpr):
        _reject_card_stat_calls(expr.target)
        if expr.key is not None:
            _reject_card_stat_calls(expr.key)
        if expr.value is not None:
            _reject_card_stat_calls(expr.value)
        return
    if isinstance(expr, ast.ListMapExpr):
        _reject_card_stat_calls(expr.target)
        _reject_card_stat_calls(expr.body)
        return
    if isinstance(expr, ast.ListFilterExpr):
        _reject_card_stat_calls(expr.target)
        _reject_card_stat_calls(expr.predicate)
        return
    if isinstance(expr, ast.ListReduceExpr):
        _reject_card_stat_calls(expr.target)
        _reject_card_stat_calls(expr.start)
        _reject_card_stat_calls(expr.body)
        return


__all__ = [
    "lower_button_item",
    "lower_link_item",
    "lower_card_group_item",
    "lower_card_item",
    "lower_column_item",
    "lower_compose_item",
    "lower_divider_item",
    "lower_drawer_item",
    "lower_modal_item",
    "lower_row_item",
    "lower_section_item",
    "lower_text_item",
    "lower_text_input_item",
    "lower_title_item",
]

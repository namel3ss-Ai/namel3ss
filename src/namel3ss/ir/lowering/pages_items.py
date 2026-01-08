from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.lowering.page_actions import _validate_overlay_action
from namel3ss.ir.lowering.page_chart import _lower_chart_item
from namel3ss.ir.lowering.page_chat import _lower_chat_item
from namel3ss.ir.lowering.page_form import _lower_form_fields, _lower_form_groups
from namel3ss.ir.lowering.page_list import _lower_list_actions, _lower_list_item_mapping
from namel3ss.ir.lowering.pages_table import (
    _lower_table_columns,
    _lower_table_pagination,
    _lower_table_row_actions,
    _lower_table_sort,
)
from namel3ss.ir.model.pages import (
    ButtonItem,
    CardAction,
    CardGroupItem,
    CardItem,
    CardStat,
    ChartItem,
    ColumnItem,
    DividerItem,
    DrawerItem,
    FormItem,
    ImageItem,
    ListItem,
    ModalItem,
    PageItem,
    RowItem,
    SectionItem,
    TabItem,
    TabsItem,
    TableItem,
    TextItem,
    TitleItem,
)
from namel3ss.schema import records as schema


def _attach_origin(target, source):
    origin = getattr(source, "origin", None)
    if origin is not None:
        setattr(target, "origin", origin)
    return target


def _lower_page_item(
    item: ast.PageItem,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_name: str,
    overlays: dict[str, set[str]],
) -> PageItem:
    if isinstance(item, ast.TitleItem):
        return _attach_origin(TitleItem(value=item.value, line=item.line, column=item.column), item)
    if isinstance(item, ast.TextItem):
        return _attach_origin(TextItem(value=item.value, line=item.line, column=item.column), item)
    if isinstance(item, ast.FormItem):
        if item.record_name not in record_map:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown record '{item.record_name}'",
                line=item.line,
                column=item.column,
            )
        record = record_map[item.record_name]
        groups = _lower_form_groups(item.groups, record, page_name)
        fields = _lower_form_fields(item.fields, record, page_name)
        return _attach_origin(
            FormItem(
                record_name=item.record_name,
                groups=groups,
                fields=fields,
                line=item.line,
                column=item.column,
            ),
            item,
        )
    if isinstance(item, ast.TableItem):
        if item.record_name not in record_map:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown record '{item.record_name}'",
                line=item.line,
                column=item.column,
            )
        record = record_map[item.record_name]
        columns = _lower_table_columns(item.columns, record)
        sort = _lower_table_sort(item.sort, record)
        pagination = _lower_table_pagination(item.pagination)
        row_actions = _lower_table_row_actions(item.row_actions, flow_names, page_name, overlays)
        return _attach_origin(
            TableItem(
                record_name=item.record_name,
                columns=columns,
                empty_text=item.empty_text,
                sort=sort,
                pagination=pagination,
                selection=item.selection,
                row_actions=row_actions,
                line=item.line,
                column=item.column,
            ),
            item,
        )
    if isinstance(item, ast.ListItem):
        if item.record_name not in record_map:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown record '{item.record_name}'",
                line=item.line,
                column=item.column,
            )
        record = record_map[item.record_name]
        variant = item.variant or "two_line"
        mapping = _lower_list_item_mapping(item.item, record, variant, item.line, item.column)
        actions = _lower_list_actions(item.actions, flow_names, page_name, overlays)
        return _attach_origin(
            ListItem(
                record_name=item.record_name,
                variant=variant,
                item=mapping,
                empty_text=item.empty_text,
                selection=item.selection,
                actions=actions,
                line=item.line,
                column=item.column,
            ),
            item,
        )
    if isinstance(item, ast.ChartItem):
        return _attach_origin(_lower_chart_item(item, record_map, page_name), item)
    if isinstance(item, ast.ChatItem):
        return _attach_origin(_lower_chat_item(item, flow_names, page_name), item)
    if isinstance(item, ast.TabsItem):
        lowered_tabs: list[TabItem] = []
        seen_labels: set[str] = set()
        for tab in item.tabs:
            if tab.label in seen_labels:
                raise Namel3ssError(
                    f"Tab label '{tab.label}' is duplicated",
                    line=tab.line,
                    column=tab.column,
                )
            seen_labels.add(tab.label)
            children = [_lower_page_item(child, record_map, flow_names, page_name, overlays) for child in tab.children]
            lowered_tab = TabItem(label=tab.label, children=children, line=tab.line, column=tab.column)
            _attach_origin(lowered_tab, tab)
            lowered_tabs.append(lowered_tab)
        if not lowered_tabs:
            raise Namel3ssError("Tabs block has no tabs", line=item.line, column=item.column)
        default_label = item.default or lowered_tabs[0].label
        if default_label not in seen_labels:
            raise Namel3ssError(
                f"Default tab '{default_label}' does not match any tab",
                line=item.line,
                column=item.column,
            )
        return _attach_origin(
            TabsItem(
                tabs=lowered_tabs,
                default=default_label,
                line=item.line,
                column=item.column,
            ),
            item,
        )
    if isinstance(item, ast.ButtonItem):
        if item.flow_name not in flow_names:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown flow '{item.flow_name}'",
                line=item.line,
                column=item.column,
            )
        return _attach_origin(
            ButtonItem(label=item.label, flow_name=item.flow_name, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.SectionItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name, overlays) for child in item.children]
        return _attach_origin(
            SectionItem(label=item.label, children=children, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.CardGroupItem):
        lowered_children: list[PageItem] = []
        for child in item.children:
            if not isinstance(child, ast.CardItem):
                raise Namel3ssError("Card groups may only contain cards", line=child.line, column=child.column)
            lowered_children.append(_lower_page_item(child, record_map, flow_names, page_name, overlays))
        return _attach_origin(CardGroupItem(children=lowered_children, line=item.line, column=item.column), item)
    if isinstance(item, ast.CardItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name, overlays) for child in item.children]
        stat = _lower_card_stat(item.stat)
        actions = _lower_card_actions(item.actions, flow_names, page_name, overlays)
        return _attach_origin(
            CardItem(label=item.label, children=children, stat=stat, actions=actions, line=item.line, column=item.column),
            item,
        )
    if isinstance(item, ast.RowItem):
        lowered_children: list[PageItem] = []
        for child in item.children:
            if not isinstance(child, ast.ColumnItem):
                raise Namel3ssError("Rows may only contain columns", line=child.line, column=child.column)
            lowered_children.append(_lower_page_item(child, record_map, flow_names, page_name, overlays))
        return _attach_origin(RowItem(children=lowered_children, line=item.line, column=item.column), item)
    if isinstance(item, ast.ColumnItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name, overlays) for child in item.children]
        return _attach_origin(ColumnItem(children=children, line=item.line, column=item.column), item)
    if isinstance(item, ast.DividerItem):
        return _attach_origin(DividerItem(line=item.line, column=item.column), item)
    if isinstance(item, ast.ImageItem):
        alt = item.alt if item.alt is not None else ""
        return _attach_origin(ImageItem(src=item.src, alt=alt, line=item.line, column=item.column), item)
    if isinstance(item, ast.ModalItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name, overlays) for child in item.children]
        return _attach_origin(ModalItem(label=item.label, children=children, line=item.line, column=item.column), item)
    if isinstance(item, ast.DrawerItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name, overlays) for child in item.children]
        return _attach_origin(DrawerItem(label=item.label, children=children, line=item.line, column=item.column), item)
    raise TypeError(f"Unhandled page item type: {type(item)}")


def _lower_card_actions(
    actions: list[ast.CardAction] | None,
    flow_names: set[str],
    page_name: str,
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
                    f"Page '{page_name}' references unknown flow '{action.flow_name}'",
                    line=action.line,
                    column=action.column,
                )
        else:
            _validate_overlay_action(action, overlays, page_name)
        if action.label in seen_labels:
            raise Namel3ssError(
                f"Card action label '{action.label}' is duplicated",
                line=action.line,
                column=action.column,
            )
        seen_labels.add(action.label)
        lowered.append(
            CardAction(
                label=action.label,
                flow_name=action.flow_name,
                kind=action.kind,
                target=action.target,
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


__all__ = ["_lower_page_item"]

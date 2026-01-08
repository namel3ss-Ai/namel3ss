from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.decl.page_actions import parse_ui_action_body
from namel3ss.parser.decl.page_chat import parse_chat_block
from namel3ss.parser.decl.page_chart import parse_chart_block, parse_chart_header
from namel3ss.parser.decl.page_form import parse_form_block
from namel3ss.parser.decl.page_list import parse_list_block
from namel3ss.parser.decl.page_table import parse_table_block


def _parse_block(
    parser,
    *,
    columns_only: bool = False,
    allow_tabs: bool = False,
    allow_overlays: bool = False,
) -> List[ast.PageItem]:
    parser._expect("NEWLINE", "Expected newline after header")
    parser._expect("INDENT", "Expected indented block")
    items: List[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if columns_only and parser._current().type != "COLUMN":
            tok = parser._current()
            raise Namel3ssError("Rows may only contain columns", line=tok.line, column=tok.column)
        items.append(parse_page_item(parser, allow_tabs=allow_tabs, allow_overlays=allow_overlays))
    parser._expect("DEDENT", "Expected end of block")
    return items


def parse_page_item(parser, *, allow_tabs: bool = False, allow_overlays: bool = False) -> ast.PageItem:
    tok = parser._current()
    if tok.type == "TITLE":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'title'")
        value_tok = parser._expect("STRING", "Expected title string")
        return ast.TitleItem(value=value_tok.value, line=tok.line, column=tok.column)
    if tok.type == "TEXT":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'text'")
        value_tok = parser._expect("STRING", "Expected text string")
        return ast.TextItem(value=value_tok.value, line=tok.line, column=tok.column)
    if tok.type == "FORM":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'form'")
        record_name = parse_reference_name(parser, context="record")
        if parser._match("COLON"):
            groups, fields = parse_form_block(parser)
            return ast.FormItem(
                record_name=record_name,
                groups=groups,
                fields=fields,
                line=tok.line,
                column=tok.column,
            )
        return ast.FormItem(record_name=record_name, line=tok.line, column=tok.column)
    if tok.type == "TABLE":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'table'")
        record_name = parse_reference_name(parser, context="record")
        if parser._match("COLON"):
            columns, empty_text, sort, pagination, selection, row_actions = parse_table_block(parser)
            return ast.TableItem(
                record_name=record_name,
                columns=columns,
                empty_text=empty_text,
                sort=sort,
                pagination=pagination,
                selection=selection,
                row_actions=row_actions,
                line=tok.line,
                column=tok.column,
            )
        return ast.TableItem(record_name=record_name, line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "list":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'list'")
        record_name = parse_reference_name(parser, context="record")
        if parser._match("COLON"):
            variant, item, empty_text, selection, actions = parse_list_block(parser)
            return ast.ListItem(
                record_name=record_name,
                variant=variant,
                item=item,
                empty_text=empty_text,
                selection=selection,
                actions=actions,
                line=tok.line,
                column=tok.column,
            )
        return ast.ListItem(record_name=record_name, line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "chart":
        parser._advance()
        record_name, source = parse_chart_header(parser)
        chart_type = None
        x = None
        y = None
        explain = None
        if parser._match("COLON"):
            chart_type, x, y, explain = parse_chart_block(parser)
        return ast.ChartItem(
            record_name=record_name,
            source=source,
            chart_type=chart_type,
            x=x,
            y=y,
            explain=explain,
            line=tok.line,
            column=tok.column,
        )
    if tok.type == "IDENT" and tok.value == "use":
        parser._advance()
        kind_tok = parser._current()
        if kind_tok.type != "IDENT" or kind_tok.value != "ui_pack":
            raise Namel3ssError("Pages only support 'use ui_pack'", line=kind_tok.line, column=kind_tok.column)
        parser._advance()
        pack_tok = parser._expect("STRING", "Expected ui_pack name string")
        frag_tok = parser._current()
        if frag_tok.type != "IDENT" or frag_tok.value != "fragment":
            raise Namel3ssError("Expected fragment name for ui_pack use", line=frag_tok.line, column=frag_tok.column)
        parser._advance()
        name_tok = parser._expect("STRING", "Expected fragment name string")
        return ast.UseUIPackItem(
            pack_name=pack_tok.value,
            fragment_name=name_tok.value,
            line=tok.line,
            column=tok.column,
        )
    if tok.type == "IDENT" and tok.value == "chat":
        parser._advance()
        parser._expect("COLON", "Expected ':' after chat")
        children = parse_chat_block(parser)
        return ast.ChatItem(children=children, line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value in {"messages", "composer", "thinking", "citations"}:
        raise Namel3ssError("Chat elements must be inside a chat block", line=tok.line, column=tok.column)
    if tok.type == "MEMORY":
        raise Namel3ssError("Chat elements must be inside a chat block", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "tabs":
        if not allow_tabs:
            raise Namel3ssError("Tabs may only appear at the page root", line=tok.line, column=tok.column)
        parser._advance()
        parser._expect("COLON", "Expected ':' after tabs")
        tabs, default_label = _parse_tabs_block(parser)
        return ast.TabsItem(tabs=tabs, default=default_label, line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "tab":
        raise Namel3ssError("Tab entries must be inside a tabs block", line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "modal":
        if not allow_overlays:
            raise Namel3ssError("Modals may only appear at the page root", line=tok.line, column=tok.column)
        parser._advance()
        label_tok = parser._expect("STRING", "Expected modal label string")
        parser._expect("COLON", "Expected ':' after modal label")
        children = _parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
        return ast.ModalItem(label=label_tok.value, children=children, line=tok.line, column=tok.column)
    if tok.type == "IDENT" and tok.value == "drawer":
        if not allow_overlays:
            raise Namel3ssError("Drawers may only appear at the page root", line=tok.line, column=tok.column)
        parser._advance()
        label_tok = parser._expect("STRING", "Expected drawer label string")
        parser._expect("COLON", "Expected ':' after drawer label")
        children = _parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
        return ast.DrawerItem(label=label_tok.value, children=children, line=tok.line, column=tok.column)
    if tok.type == "BUTTON":
        parser._advance()
        label_tok = parser._expect("STRING", "Expected button label string")
        if parser._match("CALLS"):
            raise Namel3ssError(
                'Buttons must use a block. Use: button "Run": NEWLINE indent calls flow "demo"',
                line=tok.line,
                column=tok.column,
            )
        parser._expect("COLON", "Expected ':' after button label")
        parser._expect("NEWLINE", "Expected newline after button header")
        parser._expect("INDENT", "Expected indented button body")
        flow_name = None
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            parser._expect("CALLS", "Expected 'calls' in button action")
            parser._expect("FLOW", "Expected 'flow' keyword in button action")
            flow_name = parse_reference_name(parser, context="flow")
            if parser._match("NEWLINE"):
                continue
            break
        parser._expect("DEDENT", "Expected end of button body")
        if flow_name is None:
            raise Namel3ssError("Button body must include 'calls flow \"<name>\"'", line=tok.line, column=tok.column)
        return ast.ButtonItem(label=label_tok.value, flow_name=flow_name, line=tok.line, column=tok.column)
    if tok.type == "SECTION":
        parser._advance()
        label_tok = parser._current() if parser._current().type == "STRING" else None
        if label_tok:
            parser._advance()
        parser._expect("COLON", "Expected ':' after section")
        children = _parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
        return ast.SectionItem(
            label=label_tok.value if label_tok else None,
            children=children,
            line=tok.line,
            column=tok.column,
        )
    if tok.type == "IDENT" and tok.value == "card_group":
        parser._advance()
        parser._expect("COLON", "Expected ':' after card_group")
        children = _parse_card_group_block(parser)
        return ast.CardGroupItem(children=children, line=tok.line, column=tok.column)
    if tok.type == "CARD":
        parser._advance()
        label_tok = parser._current() if parser._current().type == "STRING" else None
        if label_tok:
            parser._advance()
        parser._expect("COLON", "Expected ':' after card")
        children, stat, actions = _parse_card_block(parser)
        return ast.CardItem(
            label=label_tok.value if label_tok else None,
            children=children,
            stat=stat,
            actions=actions,
            line=tok.line,
            column=tok.column,
        )
    if tok.type == "ROW":
        parser._advance()
        parser._expect("COLON", "Expected ':' after row")
        children = _parse_block(parser, columns_only=True, allow_tabs=False, allow_overlays=False)
        return ast.RowItem(children=children, line=tok.line, column=tok.column)
    if tok.type == "COLUMN":
        parser._advance()
        parser._expect("COLON", "Expected ':' after column")
        children = _parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
        return ast.ColumnItem(children=children, line=tok.line, column=tok.column)
    if tok.type == "DIVIDER":
        parser._advance()
        return ast.DividerItem(line=tok.line, column=tok.column)
    if tok.type == "IMAGE":
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'image'")
        value_tok = parser._expect("STRING", "Expected image source string")
        return ast.ImageItem(src=value_tok.value, alt=None, line=tok.line, column=tok.column)
    raise Namel3ssError(
        f"Pages are declarative; unexpected item '{tok.type.lower()}'",
        line=tok.line,
        column=tok.column,
    )


def _parse_card_group_block(parser) -> List[ast.PageItem]:
    parser._expect("NEWLINE", "Expected newline after card_group header")
    parser._expect("INDENT", "Expected indented card_group body")
    items: List[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "CARD":
            raise Namel3ssError("Card groups may only contain cards", line=tok.line, column=tok.column)
        items.append(parse_page_item(parser, allow_tabs=False))
    parser._expect("DEDENT", "Expected end of card_group body")
    return items


def _parse_card_block(parser) -> tuple[List[ast.PageItem], ast.CardStat | None, List[ast.CardAction] | None]:
    parser._expect("NEWLINE", "Expected newline after card header")
    parser._expect("INDENT", "Expected indented card body")
    children: List[ast.PageItem] = []
    stat: ast.CardStat | None = None
    actions: List[ast.CardAction] | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "stat":
            if stat is not None:
                raise Namel3ssError("Stat block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            stat = _parse_card_stat_block(parser, tok.line, tok.column)
            continue
        if tok.type == "IDENT" and tok.value == "actions":
            if actions is not None:
                raise Namel3ssError("Actions block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            actions = _parse_card_actions_block(parser)
            continue
        children.append(parse_page_item(parser, allow_tabs=False))
    parser._expect("DEDENT", "Expected end of card body")
    return children, stat, actions


def _parse_tabs_block(parser) -> tuple[List[ast.TabItem], str | None]:
    parser._expect("NEWLINE", "Expected newline after tabs")
    parser._expect("INDENT", "Expected indented tabs body")
    tabs: List[ast.TabItem] = []
    seen_labels: set[str] = set()
    default_label: str | None = None
    default_line: int | None = None
    default_column: int | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "default":
            if default_label is not None:
                raise Namel3ssError("Default tab is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after default")
            value_tok = parser._expect("STRING", "Expected default tab label string")
            default_label = value_tok.value
            default_line = value_tok.line
            default_column = value_tok.column
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "tab":
            parser._advance()
            label_tok = parser._expect("STRING", "Expected tab label string")
            if label_tok.value in seen_labels:
                raise Namel3ssError(
                    f"Tab label '{label_tok.value}' is duplicated",
                    line=label_tok.line,
                    column=label_tok.column,
                )
            seen_labels.add(label_tok.value)
            parser._expect("COLON", "Expected ':' after tab label")
            children = _parse_block(parser, columns_only=False, allow_tabs=False)
            tabs.append(ast.TabItem(label=label_tok.value, children=children, line=tok.line, column=tok.column))
            continue
        raise Namel3ssError("Tabs may only contain tab entries", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of tabs body")
    if not tabs:
        tok = parser._current()
        raise Namel3ssError("Tabs block has no tabs", line=tok.line, column=tok.column)
    if default_label is not None and default_label not in seen_labels:
        raise Namel3ssError(
            f"Default tab '{default_label}' does not match any tab",
            line=default_line,
            column=default_column,
        )
    return tabs, default_label


def _parse_card_stat_block(parser, line: int, column: int) -> ast.CardStat:
    parser._expect("COLON", "Expected ':' after stat")
    parser._expect("NEWLINE", "Expected newline after stat")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Stat block has no entries", line=tok.line, column=tok.column)
    label: str | None = None
    value_expr: ast.Expression | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "value":
            if value_expr is not None:
                raise Namel3ssError("Stat value is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after value")
            value_expr = parser._parse_expression()
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "label":
            if label is not None:
                raise Namel3ssError("Stat label is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after label")
            value_tok = parser._expect("STRING", "Expected label string")
            label = value_tok.value
            if parser._match("NEWLINE"):
                continue
            continue
        raise Namel3ssError(
            f"Unknown stat setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of stat block")
    if value_expr is None:
        raise Namel3ssError("Stat block requires value", line=line, column=column)
    return ast.CardStat(value=value_expr, label=label, line=line, column=column)


def _parse_card_actions_block(parser) -> List[ast.CardAction]:
    parser._expect("COLON", "Expected ':' after actions")
    parser._expect("NEWLINE", "Expected newline after actions")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Actions block has no entries", line=tok.line, column=tok.column)
    actions: List[ast.CardAction] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT" or tok.value != "action":
            raise Namel3ssError("Actions may only contain action entries", line=tok.line, column=tok.column)
        parser._advance()
        label_tok = parser._expect("STRING", "Expected action label string")
        if parser._match("CALLS"):
            raise Namel3ssError(
                'Actions must use a block. Use: action "Label": NEWLINE indent calls flow "demo"',
                line=tok.line,
                column=tok.column,
            )
        parser._expect("COLON", "Expected ':' after action label")
        parser._expect("NEWLINE", "Expected newline after action header")
        parser._expect("INDENT", "Expected indented action body")
        kind = None
        flow_name = None
        target = None
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            kind, flow_name, target = parse_ui_action_body(parser, entry_label="Action")
            if parser._match("NEWLINE"):
                continue
            break
        parser._expect("DEDENT", "Expected end of action body")
        if kind is None:
            raise Namel3ssError("Action body must include 'calls flow \"<name>\"'", line=tok.line, column=tok.column)
        if kind == "call_flow" and flow_name is None:
            raise Namel3ssError("Action body must include 'calls flow \"<name>\"'", line=tok.line, column=tok.column)
        if kind != "call_flow" and target is None:
            raise Namel3ssError("Action body must include a modal or drawer target", line=tok.line, column=tok.column)
        actions.append(
            ast.CardAction(
                label=label_tok.value,
                flow_name=flow_name,
                kind=kind,
                target=target,
                line=tok.line,
                column=tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of actions block")
    if not actions:
        raise Namel3ssError("Actions block has no entries", line=parser._current().line, column=parser._current().column)
    return actions


__all__ = ["parse_page_item"]

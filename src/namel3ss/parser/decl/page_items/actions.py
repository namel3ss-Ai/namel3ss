from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.core.helpers import parse_reference_name
from namel3ss.parser.decl.page_actions import parse_ui_action_body


def parse_compose_item(parser, tok, parse_block) -> ast.ComposeItem:
    parser._advance()
    name_tok = parser._expect("IDENT", "Expected compose name")
    if is_keyword(name_tok.value):
        raise Namel3ssError(
            f"Compose name '{name_tok.value}' is reserved",
            line=name_tok.line,
            column=name_tok.column,
        )
    parser._expect("COLON", "Expected ':' after compose name")
    children = parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
    return ast.ComposeItem(name=name_tok.value, children=children, line=tok.line, column=tok.column)


def parse_modal_item(parser, tok, parse_block, *, allow_overlays: bool) -> ast.ModalItem:
    if not allow_overlays:
        raise Namel3ssError("Modals may only appear at the page root", line=tok.line, column=tok.column)
    parser._advance()
    label_tok = parser._expect("STRING", "Expected modal label string")
    parser._expect("COLON", "Expected ':' after modal label")
    children = parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
    return ast.ModalItem(label=label_tok.value, children=children, line=tok.line, column=tok.column)


def parse_drawer_item(parser, tok, parse_block, *, allow_overlays: bool) -> ast.DrawerItem:
    if not allow_overlays:
        raise Namel3ssError("Drawers may only appear at the page root", line=tok.line, column=tok.column)
    parser._advance()
    label_tok = parser._expect("STRING", "Expected drawer label string")
    parser._expect("COLON", "Expected ':' after drawer label")
    children = parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
    return ast.DrawerItem(label=label_tok.value, children=children, line=tok.line, column=tok.column)


def parse_button_item(parser, tok) -> ast.ButtonItem:
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
        tok_action = parser._current()
        if tok_action.type == "CALLS":
            parser._advance()
            parser._expect("FLOW", "Expected 'flow' keyword in button action")
            flow_name = parse_reference_name(parser, context="flow")
            parser._match("NEWLINE")
            continue
        if tok_action.type == "IDENT" and tok_action.value == "runs":
            parser._advance()
            flow_name = parse_reference_name(parser, context="flow")
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            "Buttons must declare an action using 'calls flow \"<name>\"' or 'runs \"<flow>\"'",
            line=tok_action.line,
            column=tok_action.column,
        )
    parser._expect("DEDENT", "Expected end of button body")
    if flow_name is None:
        raise Namel3ssError(
            "Button body must include 'calls flow \"<name>\"' or 'runs \"<flow>\"'",
            line=tok.line,
            column=tok.column,
        )
    return ast.ButtonItem(label=label_tok.value, flow_name=flow_name, line=tok.line, column=tok.column)


def parse_section_item(parser, tok, parse_block) -> ast.SectionItem:
    parser._advance()
    label_tok = parser._current() if parser._current().type == "STRING" else None
    if label_tok:
        parser._advance()
    parser._expect("COLON", "Expected ':' after section")
    children = parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
    return ast.SectionItem(
        label=label_tok.value if label_tok else None,
        children=children,
        line=tok.line,
        column=tok.column,
    )


def parse_card_group_item(parser, tok, parse_page_item) -> ast.CardGroupItem:
    parser._advance()
    parser._expect("COLON", "Expected ':' after card_group")
    children = _parse_card_group_block(parser, parse_page_item)
    return ast.CardGroupItem(children=children, line=tok.line, column=tok.column)


def parse_card_item(parser, tok, parse_page_item) -> ast.CardItem:
    parser._advance()
    label_tok = parser._current() if parser._current().type == "STRING" else None
    if label_tok:
        parser._advance()
    parser._expect("COLON", "Expected ':' after card")
    children, stat, actions = _parse_card_block(parser, parse_page_item)
    return ast.CardItem(
        label=label_tok.value if label_tok else None,
        children=children,
        stat=stat,
        actions=actions,
        line=tok.line,
        column=tok.column,
    )


def parse_row_item(parser, tok, parse_block) -> ast.RowItem:
    parser._advance()
    parser._expect("COLON", "Expected ':' after row")
    children = parse_block(parser, columns_only=True, allow_tabs=False, allow_overlays=False)
    return ast.RowItem(children=children, line=tok.line, column=tok.column)


def parse_column_item(parser, tok, parse_block) -> ast.ColumnItem:
    parser._advance()
    parser._expect("COLON", "Expected ':' after column")
    children = parse_block(parser, columns_only=False, allow_tabs=False, allow_overlays=False)
    return ast.ColumnItem(children=children, line=tok.line, column=tok.column)


def parse_divider_item(parser, tok) -> ast.DividerItem:
    parser._advance()
    return ast.DividerItem(line=tok.line, column=tok.column)


def _parse_card_group_block(parser, parse_page_item) -> List[ast.PageItem]:
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


def _parse_card_block(parser, parse_page_item) -> tuple[List[ast.PageItem], ast.CardStat | None, List[ast.CardAction] | None]:
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


__all__ = [
    "parse_button_item",
    "parse_card_group_item",
    "parse_card_item",
    "parse_column_item",
    "parse_compose_item",
    "parse_divider_item",
    "parse_drawer_item",
    "parse_modal_item",
    "parse_row_item",
    "parse_section_item",
]

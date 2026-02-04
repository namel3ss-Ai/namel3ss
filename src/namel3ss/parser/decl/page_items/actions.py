from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_common import (
    _parse_action_availability_rule_block,
    _is_visibility_rule_start,
    _parse_optional_string_value,
    _parse_reference_name_value,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic

from .cards import parse_card_group_item, parse_card_item

def parse_compose_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.ComposeItem:
    parser._advance()
    name_tok = parser._expect("IDENT", "Expected compose name")
    if is_keyword(name_tok.value) and not getattr(name_tok, "escaped", False):
        guidance, details = reserved_identifier_diagnostic(name_tok.value)
        raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after compose name")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ComposeItem(
        name=name_tok.value,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_modal_item(
    parser,
    tok,
    parse_block,
    *,
    allow_overlays: bool,
    allow_pattern_params: bool = False,
) -> ast.ModalItem:
    if not allow_overlays:
        raise Namel3ssError("Modals may only appear at the page root", line=tok.line, column=tok.column)
    parser._advance()
    label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="modal label")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after modal label")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ModalItem(
        label=label,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_drawer_item(
    parser,
    tok,
    parse_block,
    *,
    allow_overlays: bool,
    allow_pattern_params: bool = False,
) -> ast.DrawerItem:
    if not allow_overlays:
        raise Namel3ssError("Drawers may only appear at the page root", line=tok.line, column=tok.column)
    parser._advance()
    label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="drawer label")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after drawer label")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.DrawerItem(
        label=label,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_button_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ButtonItem:
    parser._advance()
    label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="button label")
    if parser._match("CALLS"):
        raise Namel3ssError(
            'Buttons must use a block. Use: button "Run": NEWLINE indent calls flow "demo"',
            line=tok.line,
            column=tok.column,
        )
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after button label")
    parser._expect("NEWLINE", "Expected newline after button header")
    parser._expect("INDENT", "Expected indented button body")
    flow_name = None
    visibility_rule = None
    availability_rule = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                tok_action = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok_action.line,
                    column=tok_action.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        tok_action = parser._current()
        if tok_action.type == "CALLS":
            parser._advance()
            parser._expect("FLOW", "Expected 'flow' keyword in button action")
            flow_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="flow")
            rule = _parse_action_availability_rule_block(parser, allow_pattern_params=allow_pattern_params)
            if rule is not None:
                if availability_rule is not None:
                    raise Namel3ssError(
                        "Action availability blocks may only declare one only-when rule.",
                        line=tok_action.line,
                        column=tok_action.column,
                    )
                availability_rule = rule
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            "Buttons must declare an action using 'calls flow \"<name>\"'",
            line=tok_action.line,
            column=tok_action.column,
        )
    parser._expect("DEDENT", "Expected end of button body")
    if flow_name is None:
        raise Namel3ssError(
            "Button body must include 'calls flow \"<name>\"'",
            line=tok.line,
            column=tok.column,
        )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ButtonItem(
        label=label,
        flow_name=flow_name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        availability_rule=availability_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_text_input_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.TextInputItem:
    parser._advance()
    type_tok = parser._current()
    if type_tok.type == "TEXT" or (type_tok.type == "IDENT" and type_tok.value == "text"):
        parser._advance()
    else:
        raise Namel3ssError("Input must declare text", line=type_tok.line, column=type_tok.column)
    parser._expect("AS", "Expected 'as' after input text")
    name_tok = parser._expect("IDENT", "Expected input name")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("NEWLINE", "Expected newline after input header")
    parser._expect("INDENT", "Expected indented input body")
    flow_name = None
    visibility_rule = None
    availability_rule = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                tok_action = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok_action.line,
                    column=tok_action.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        tok_action = parser._current()
        if tok_action.type == "IDENT" and tok_action.value == "send":
            parser._advance()
            parser._expect("TO", "Expected 'to' after send")
            parser._expect("FLOW", "Expected 'flow' after send to")
            if flow_name is not None:
                raise Namel3ssError("Send to flow is declared more than once", line=tok_action.line, column=tok_action.column)
            flow_name = _parse_reference_name_value(parser, allow_pattern_params=allow_pattern_params, context="flow")
            rule = _parse_action_availability_rule_block(parser, allow_pattern_params=allow_pattern_params)
            if rule is not None:
                if availability_rule is not None:
                    raise Namel3ssError(
                        "Action availability blocks may only declare one only-when rule.",
                        line=tok_action.line,
                        column=tok_action.column,
                    )
                availability_rule = rule
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            "Input must declare 'send to flow \"<name>\"'",
            line=tok_action.line,
            column=tok_action.column,
        )
    parser._expect("DEDENT", "Expected end of input body")
    if flow_name is None:
        raise Namel3ssError(
            "Input body must include 'send to flow \"<name>\"'",
            line=tok.line,
            column=tok.column,
        )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.TextInputItem(
        name=name_tok.value,
        flow_name=flow_name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        availability_rule=availability_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_link_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.LinkItem:
    parser._advance()
    label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="link label")
    parser._expect("TO", "Expected 'to' after link label")
    page_tok = parser._current()
    if page_tok.type != "PAGE":
        raise Namel3ssError("Expected 'page' after 'to'", line=page_tok.line, column=page_tok.column)
    parser._advance()
    name = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="page name")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.LinkItem(
        label=label,
        page_name=name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_section_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.SectionItem:
    parser._advance()
    label = _parse_optional_string_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after section")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.SectionItem(
        label=label,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_row_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.RowItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after row")
    children, visibility_rule = parse_block(
        parser,
        columns_only=True,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.RowItem(
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_column_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.ColumnItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after column")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ColumnItem(
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


def parse_divider_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.DividerItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.DividerItem(
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


__all__ = [
    "parse_button_item",
    "parse_link_item",
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

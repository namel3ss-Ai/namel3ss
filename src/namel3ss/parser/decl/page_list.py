from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_actions import parse_ui_action_body
from namel3ss.parser.decl.page_common import _is_visibility_rule_start, _parse_string_value, _parse_visibility_rule_line
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic


def parse_list_block(parser, *, allow_pattern_params: bool = False):
    parser._expect("NEWLINE", "Expected newline after list header")
    parser._expect("INDENT", "Expected indented list block")
    variant = None
    item = None
    empty_text = None
    empty_state_hidden = False
    selection = None
    actions = None
    visibility_rule = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=tok.line, column=tok.column)
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "variant":
            if variant is not None:
                raise Namel3ssError("Variant is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after variant")
            value_tok = parser._current()
            if value_tok.type not in {"STRING", "IDENT"}:
                raise Namel3ssError(
                    "Variant must be 'single_line', 'two_line', or 'icon'",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            parser._advance()
            variant_value = str(value_tok.value).lower()
            if variant_value not in {"single_line", "two_line", "icon"}:
                raise Namel3ssError(
                    "Variant must be 'single_line', 'two_line', or 'icon'",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            variant = variant_value
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "item":
            if item is not None:
                raise Namel3ssError("Item block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            item = _parse_list_item_block(parser, tok.line, tok.column)
            continue
        if tok.type == "IDENT" and tok.value == "empty_state":
            if empty_text is not None or empty_state_hidden:
                raise Namel3ssError("Empty state is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            empty_text, empty_state_hidden = _parse_empty_state_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        if tok.type == "IDENT" and tok.value == "empty_text":
            if empty_text is not None or empty_state_hidden:
                raise Namel3ssError("Empty state is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after empty_text")
            empty_text = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="empty state")
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "selection":
            if selection is not None:
                raise Namel3ssError("Selection is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after selection")
            value_tok = parser._current()
            if value_tok.type not in {"STRING", "IDENT"}:
                raise Namel3ssError(
                    "Selection must be 'none', 'single', or 'multi'",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            parser._advance()
            selection_value = str(value_tok.value).lower()
            if selection_value not in {"none", "single", "multi"}:
                raise Namel3ssError(
                    "Selection must be 'none', 'single', or 'multi'",
                    line=value_tok.line,
                    column=value_tok.column,
                )
            selection = selection_value
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "actions":
            if actions is not None:
                raise Namel3ssError("Actions block is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            actions = _parse_list_actions_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        raise Namel3ssError(
            f"Unknown list setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of list block")
    return variant, item, empty_text, empty_state_hidden, selection, actions, visibility_rule


def _parse_list_item_block(parser, line: int, column: int) -> ast.ListItemMapping:
    parser._expect("COLON", "Expected ':' after item")
    parser._expect("NEWLINE", "Expected newline after item")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Item block has no entries", line=tok.line, column=tok.column)
    primary = None
    secondary = None
    meta = None
    icon = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "primary":
            if primary is not None:
                raise Namel3ssError("Primary is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after primary")
            primary = _parse_list_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "secondary":
            if secondary is not None:
                raise Namel3ssError("Secondary is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after secondary")
            secondary = _parse_list_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "meta":
            if meta is not None:
                raise Namel3ssError("Meta is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after meta")
            meta = _parse_list_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        if tok.type == "IDENT" and tok.value == "icon":
            if icon is not None:
                raise Namel3ssError("Icon is declared more than once", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after icon")
            icon = _parse_list_field_name(parser)
            if parser._match("NEWLINE"):
                continue
            continue
        raise Namel3ssError(
            f"Unknown item setting '{tok.value}'",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of item block")
    if primary is None:
        raise Namel3ssError("Item block requires primary", line=line, column=column)
    return ast.ListItemMapping(
        primary=primary,
        secondary=secondary,
        meta=meta,
        icon=icon,
        line=line,
        column=column,
    )


def _parse_empty_state_block(parser, *, allow_pattern_params: bool = False) -> tuple[str | None, bool]:
    parser._expect("COLON", "Expected ':' after empty_state")
    tok = parser._current()
    if tok.type != "NEWLINE":
        if tok.type == "BOOLEAN":
            parser._advance()
            if bool(tok.value):
                raise Namel3ssError(
                    "empty_state inline value only supports hidden or false.",
                    line=tok.line,
                    column=tok.column,
                )
            if parser._current().type not in {"NEWLINE", "DEDENT", "COLON"}:
                extra = parser._current()
                raise Namel3ssError("empty_state inline value must end at the line boundary.", line=extra.line, column=extra.column)
            return None, True
        if tok.type in {"IDENT", "STRING"}:
            parser._advance()
            if str(tok.value).strip().lower() != "hidden":
                raise Namel3ssError(
                    "empty_state inline value only supports hidden or false.",
                    line=tok.line,
                    column=tok.column,
                )
            if parser._current().type not in {"NEWLINE", "DEDENT", "COLON"}:
                extra = parser._current()
                raise Namel3ssError("empty_state inline value must end at the line boundary.", line=extra.line, column=extra.column)
            return None, True
        raise Namel3ssError(
            "empty_state must be a text block or set to hidden/false.",
            line=tok.line,
            column=tok.column,
        )
    parser._expect("NEWLINE", "Expected newline after empty_state")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Empty state block has no entries", line=tok.line, column=tok.column)
    text_value: str | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "TEXT":
            raise Namel3ssError("Empty state only supports text", line=tok.line, column=tok.column)
        parser._advance()
        parser._expect("IS", "Expected 'is' after 'text'")
        value_tok = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="empty state")
        if text_value is not None:
            raise Namel3ssError("Empty state only supports one text entry", line=tok.line, column=tok.column)
        text_value = value_tok
        if parser._match("NEWLINE"):
            continue
    parser._expect("DEDENT", "Expected end of empty_state block")
    if text_value is None:
        tok = parser._current()
        raise Namel3ssError("Empty state block has no entries", line=tok.line, column=tok.column)
    return text_value, False


def _parse_list_actions_block(parser, *, allow_pattern_params: bool) -> List[ast.ListAction]:
    parser._expect("COLON", "Expected ':' after actions")
    parser._expect("NEWLINE", "Expected newline after actions")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError("Actions block has no entries", line=tok.line, column=tok.column)
    actions: List[ast.ListAction] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type != "IDENT" or tok.value != "action":
            raise Namel3ssError("Actions may only contain action entries", line=tok.line, column=tok.column)
        parser._advance()
        label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="action label")
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
        availability_rule = None
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            kind, flow_name, target, availability_rule = parse_ui_action_body(
                parser,
                entry_label="Action",
                allow_pattern_params=allow_pattern_params,
            )
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
            ast.ListAction(
                label=label,
                flow_name=flow_name,
                kind=kind,
                target=target,
                availability_rule=availability_rule,
                line=tok.line,
                column=tok.column,
            )
        )
    parser._expect("DEDENT", "Expected end of actions block")
    if not actions:
        raise Namel3ssError("Actions block has no entries", line=parser._current().line, column=parser._current().column)
    return actions


def _parse_list_field_name(parser) -> str:
    tok = parser._current()
    if tok.type in {"STRING", "IDENT"}:
        parser._advance()
        return str(tok.value)
    if isinstance(tok.value, str) and is_keyword(tok.value):
        guidance, details = reserved_identifier_diagnostic(tok.value)
        raise Namel3ssError(guidance, line=tok.line, column=tok.column, details=details)
    raise Namel3ssError("Expected field name", line=tok.line, column=tok.column)


__all__ = ["parse_list_block"]

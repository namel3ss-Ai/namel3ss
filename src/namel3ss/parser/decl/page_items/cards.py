from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_actions import parse_ui_action_body
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _is_visibility_rule_start,
    _parse_optional_string_value,
    _parse_style_hooks_block,
    _parse_variant_line,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)
from .size_radius import apply_theme_override, parse_theme_override_line


def parse_card_group_item(parser, tok, parse_page_item, *, allow_pattern_params: bool = False) -> ast.CardGroupItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after card_group")
    children, visibility_rule = _parse_card_group_block(parser, parse_page_item, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.CardGroupItem(
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_card_item(parser, tok, parse_page_item, *, allow_pattern_params: bool = False) -> ast.CardItem:
    parser._advance()
    label = _parse_optional_string_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after card")
    children, stat, actions, visibility_rule, variant, style_hooks, theme_overrides = _parse_card_block(
        parser,
        parse_page_item,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    item = ast.CardItem(
        label=label,
        children=children,
        stat=stat,
        actions=actions,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )
    if variant is not None:
        setattr(item, "variant", variant)
    if style_hooks is not None:
        setattr(item, "style_hooks", style_hooks)
    if theme_overrides is not None:
        setattr(item, "theme_overrides", theme_overrides)
    return item


def _parse_card_group_block(
    parser,
    parse_page_item,
    *,
    allow_pattern_params: bool,
) -> tuple[List[ast.PageItem], ast.VisibilityRule | None]:
    parser._expect("NEWLINE", "Expected newline after card_group header")
    parser._expect("INDENT", "Expected indented card_group body")
    items: List[ast.PageItem] = []
    visibility_rule: ast.VisibilityRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                tok = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok.line,
                    column=tok.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        tok = parser._current()
        if tok.type != "CARD":
            raise Namel3ssError("Card groups may only contain cards", line=tok.line, column=tok.column)
        parsed = parse_page_item(parser, allow_tabs=False, allow_pattern_params=allow_pattern_params)
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", "Expected end of card_group body")
    return items, visibility_rule


def _parse_card_block(
    parser,
    parse_page_item,
    *,
    allow_pattern_params: bool,
) -> tuple[
    List[ast.PageItem],
    ast.CardStat | None,
    List[ast.CardAction] | None,
    ast.VisibilityRule | None,
    str | None,
    dict[str, str] | None,
    ast.ThemeTokenOverrides | None,
]:
    parser._expect("NEWLINE", "Expected newline after card header")
    parser._expect("INDENT", "Expected indented card body")
    children: List[ast.PageItem] = []
    stat: ast.CardStat | None = None
    actions: List[ast.CardAction] | None = None
    visibility_rule: ast.VisibilityRule | None = None
    variant: str | None = None
    style_hooks: dict[str, str] | None = None
    theme_overrides: ast.ThemeTokenOverrides | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                tok = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok.line,
                    column=tok.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        tok = parser._current()
        token_name, override = parse_theme_override_line(parser)
        if override is not None and token_name is not None:
            theme_overrides = apply_theme_override(
                theme_overrides,
                override,
                token_name=token_name,
                line=override.line,
                column=override.column,
            )
            parser._match("NEWLINE")
            continue
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
            actions = _parse_card_actions_block(parser, allow_pattern_params=allow_pattern_params)
            continue
        if tok.type == "IDENT" and tok.value == "variant":
            if variant is not None:
                raise Namel3ssError("Variant is declared more than once", line=tok.line, column=tok.column)
            variant = _parse_variant_line(parser)
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "style_hooks":
            if style_hooks is not None:
                raise Namel3ssError("style_hooks is declared more than once", line=tok.line, column=tok.column)
            style_hooks = _parse_style_hooks_block(parser)
            parser._match("NEWLINE")
            continue
        parsed = parse_page_item(parser, allow_tabs=False, allow_pattern_params=allow_pattern_params)
        if isinstance(parsed, list):
            children.extend(parsed)
        else:
            children.append(parsed)
    parser._expect("DEDENT", "Expected end of card body")
    return children, stat, actions, visibility_rule, variant, style_hooks, theme_overrides


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


def _parse_card_actions_block(parser, *, allow_pattern_params: bool) -> List[ast.CardAction]:
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
        if kind in {"open_modal", "close_modal", "open_drawer", "close_drawer", "navigate_to"} and target is None:
            raise Namel3ssError(
                "Action body must include a modal/drawer target or navigation page.",
                line=tok.line,
                column=tok.column,
            )
        actions.append(
            ast.CardAction(
                label=label_tok.value,
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


__all__ = ["parse_card_group_item", "parse_card_item"]

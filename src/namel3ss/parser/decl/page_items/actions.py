from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.icons.registry import validate_icon_name
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_common import (
    _parse_action_availability_rule_block,
    _parse_debug_only_clause,
    _is_visibility_rule_start,
    _parse_reference_name_value,
    _parse_style_hooks_block,
    _parse_string_value,
    _parse_variant_line,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic

from .cards import parse_card_group_item, parse_card_item
from .size_radius import apply_theme_override, parse_theme_override_line

def parse_compose_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.ComposeItem:
    parser._advance()
    name_tok = parser._expect("IDENT", "Expected compose name")
    if is_keyword(name_tok.value) and not getattr(name_tok, "escaped", False):
        guidance, details = reserved_identifier_diagnostic(name_tok.value)
        raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
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
        show_when=show_when,
        debug_only=debug_only,
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
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
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
        show_when=show_when,
        debug_only=debug_only,
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
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
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
        show_when=show_when,
        debug_only=debug_only,
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
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after button label")
    parser._expect("NEWLINE", "Expected newline after button header")
    parser._expect("INDENT", "Expected indented button body")
    action_kind: str | None = None
    flow_name: str | None = None
    target: str | None = None
    visibility_rule = None
    availability_rule = None
    icon = None
    variant = None
    style_hooks = None
    theme_overrides: ast.ThemeTokenOverrides | None = None
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
        if tok_action.type == "IDENT" and tok_action.value == "variant":
            if variant is not None:
                raise Namel3ssError("Variant is declared more than once", line=tok_action.line, column=tok_action.column)
            variant = _parse_variant_line(parser)
            parser._match("NEWLINE")
            continue
        if tok_action.type == "IDENT" and tok_action.value == "style_hooks":
            if style_hooks is not None:
                raise Namel3ssError("style_hooks is declared more than once", line=tok_action.line, column=tok_action.column)
            style_hooks = _parse_style_hooks_block(parser)
            parser._match("NEWLINE")
            continue
        if tok_action.type == "IDENT" and tok_action.value == "icon":
            if icon is not None:
                raise Namel3ssError("Icon is declared more than once", line=tok_action.line, column=tok_action.column)
            parser._advance()
            if parser._match("COLON"):
                pass
            else:
                parser._expect("IS", "Expected ':' or 'is' after icon")
            value_tok = parser._current()
            if value_tok.type not in {"STRING", "IDENT"}:
                raise Namel3ssError("icon must be an identifier or string", line=value_tok.line, column=value_tok.column)
            parser._advance()
            icon = validate_icon_name(str(value_tok.value), line=value_tok.line, column=value_tok.column)
            parser._match("NEWLINE")
            continue
        if tok_action.type == "CALLS":
            if action_kind is not None:
                raise Namel3ssError(
                    "Button body can only declare one action.",
                    line=tok_action.line,
                    column=tok_action.column,
                )
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
            action_kind = "call_flow"
            parser._match("NEWLINE")
            continue
        if tok_action.type == "IDENT" and tok_action.value == "navigate_to":
            if action_kind is not None:
                raise Namel3ssError(
                    "Button body can only declare one action.",
                    line=tok_action.line,
                    column=tok_action.column,
                )
            parser._advance()
            target = _parse_string_value(
                parser,
                allow_pattern_params=allow_pattern_params,
                context="navigation target page",
            )
            rule = _parse_action_availability_rule_block(parser, allow_pattern_params=allow_pattern_params)
            if rule is not None:
                if availability_rule is not None:
                    raise Namel3ssError(
                        "Action availability blocks may only declare one only-when rule.",
                        line=tok_action.line,
                        column=tok_action.column,
                    )
                availability_rule = rule
            action_kind = "navigate_to"
            parser._match("NEWLINE")
            continue
        if tok_action.type == "IDENT" and tok_action.value == "go_back":
            if action_kind is not None:
                raise Namel3ssError(
                    "Button body can only declare one action.",
                    line=tok_action.line,
                    column=tok_action.column,
                )
            parser._advance()
            rule = _parse_action_availability_rule_block(parser, allow_pattern_params=allow_pattern_params)
            if rule is not None:
                if availability_rule is not None:
                    raise Namel3ssError(
                        "Action availability blocks may only declare one only-when rule.",
                        line=tok_action.line,
                        column=tok_action.column,
                    )
                availability_rule = rule
            action_kind = "go_back"
            parser._match("NEWLINE")
            continue
        raise Namel3ssError(
            "Buttons must declare one action: 'calls flow \"<name>\"', 'navigate_to \"<page>\"', or 'go_back'",
            line=tok_action.line,
            column=tok_action.column,
        )
    parser._expect("DEDENT", "Expected end of button body")
    if action_kind is None:
        raise Namel3ssError(
            "Button body must include one action.",
            line=tok.line,
            column=tok.column,
        )
    if action_kind == "call_flow" and flow_name is None:
        raise Namel3ssError(
            "Button body must include 'calls flow \"<name>\"'",
            line=tok.line,
            column=tok.column,
        )
    if action_kind == "navigate_to" and target is None:
        raise Namel3ssError(
            "Button body must include 'navigate_to \"<page>\"'",
            line=tok.line,
            column=tok.column,
        )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    item = ast.ButtonItem(
        label=label,
        flow_name=flow_name,
        action_kind=action_kind,
        target=target,
        icon=icon,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        availability_rule=availability_rule,
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
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("NEWLINE", "Expected newline after input header")
    parser._expect("INDENT", "Expected indented input body")
    flow_name = None
    visibility_rule = None
    availability_rule = None
    theme_overrides: ast.ThemeTokenOverrides | None = None
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
    item = ast.TextInputItem(
        name=name_tok.value,
        flow_name=flow_name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        availability_rule=availability_rule,
        line=tok.line,
        column=tok.column,
    )
    if theme_overrides is not None:
        setattr(item, "theme_overrides", theme_overrides)
    return item


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
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.LinkItem(
        label=label,
        page_name=name,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


__all__ = [
    "parse_button_item",
    "parse_link_item",
    "parse_card_group_item",
    "parse_card_item",
    "parse_compose_item",
    "parse_drawer_item",
    "parse_modal_item",
]

from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _is_debug_only_start,
    _is_param_ref,
    _is_visibility_rule_start,
    _parse_debug_only_clause,
    _parse_debug_only_line,
    _parse_param_ref,
    _parse_state_path_value_relaxed,
    _parse_visibility_clause,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)

_COMPONENT_METADATA_KEYS = {"visibility", "visible_when", "when", "debug_only", "only"}


def parse_custom_component_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.CustomComponentItem:
    parser._advance()
    props: list[ast.CustomComponentProp] = []
    seen_props: set[str] = set()

    _parse_inline_properties(parser, props=props, seen_props=seen_props, allow_pattern_params=allow_pattern_params)

    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)

    visibility_rule = None
    if parser._match("COLON"):
        visibility_rule, debug_only = _parse_component_block(
            parser,
            props=props,
            seen_props=seen_props,
            allow_pattern_params=allow_pattern_params,
            debug_only=debug_only,
        )
    elif _has_continuation_block(parser):
        parser._expect("NEWLINE", "Expected newline before component settings")
        visibility_rule, debug_only = _parse_component_block_body(
            parser,
            props=props,
            seen_props=seen_props,
            allow_pattern_params=allow_pattern_params,
            debug_only=debug_only,
        )
    else:
        visibility_rule = None

    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.CustomComponentItem(
        component_name=str(tok.value),
        properties=props,
        visibility=visibility,
        visibility_rule=visibility_rule,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_component_block(
    parser,
    *,
    props: list[ast.CustomComponentProp],
    seen_props: set[str],
    allow_pattern_params: bool,
    debug_only: bool | None,
) -> tuple[ast.VisibilityRule | ast.VisibilityExpressionRule | None, bool | None]:
    parser._expect("NEWLINE", "Expected newline after component header")
    return _parse_component_block_body(
        parser,
        props=props,
        seen_props=seen_props,
        allow_pattern_params=allow_pattern_params,
        debug_only=debug_only,
    )


def _parse_component_block_body(
    parser,
    *,
    props: list[ast.CustomComponentProp],
    seen_props: set[str],
    allow_pattern_params: bool,
    debug_only: bool | None,
) -> tuple[ast.VisibilityRule | ast.VisibilityExpressionRule | None, bool | None]:
    parser._expect("INDENT", "Expected indented component block")
    visibility_rule: ast.VisibilityRule | ast.VisibilityExpressionRule | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=tok.line,
                    column=tok.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        if _is_debug_only_start(parser):
            if debug_only is not None:
                raise Namel3ssError("debug_only is already declared for this component", line=tok.line, column=tok.column)
            debug_only = _parse_debug_only_line(parser)
            parser._match("NEWLINE")
            continue
        _parse_property_line(
            parser,
            props=props,
            seen_props=seen_props,
            allow_pattern_params=allow_pattern_params,
        )
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of component block")
    return visibility_rule, debug_only


def _parse_inline_properties(
    parser,
    *,
    props: list[ast.CustomComponentProp],
    seen_props: set[str],
    allow_pattern_params: bool,
) -> None:
    while _can_parse_property_entry(parser):
        _parse_property_line(
            parser,
            props=props,
            seen_props=seen_props,
            allow_pattern_params=allow_pattern_params,
        )


def _parse_property_line(
    parser,
    *,
    props: list[ast.CustomComponentProp],
    seen_props: set[str],
    allow_pattern_params: bool,
) -> None:
    key_tok = parser._current()
    if key_tok.type != "IDENT":
        raise Namel3ssError("Expected component property name", line=key_tok.line, column=key_tok.column)
    key = str(key_tok.value)
    if key in _COMPONENT_METADATA_KEYS:
        raise Namel3ssError(
            f"'{key}' is reserved component metadata and cannot be used as a property name.",
            line=key_tok.line,
            column=key_tok.column,
        )
    parser._advance()
    parser._expect("COLON", "Expected ':' after component property name")
    value = _parse_property_value(parser, allow_pattern_params=allow_pattern_params)
    if key in seen_props:
        raise Namel3ssError(f"Component property '{key}' is declared more than once", line=key_tok.line, column=key_tok.column)
    seen_props.add(key)
    props.append(ast.CustomComponentProp(name=key, value=value, line=key_tok.line, column=key_tok.column))


def _parse_property_value(parser, *, allow_pattern_params: bool) -> object:
    tok = parser._current()
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    if tok.type == "STATE":
        return _parse_state_path_value_relaxed(parser, allow_pattern_params=False)
    if tok.type == "STRING":
        parser._advance()
        return str(tok.value)
    if tok.type == "NUMBER":
        parser._advance()
        return tok.value
    if tok.type == "BOOLEAN":
        parser._advance()
        return bool(tok.value)
    if tok.type == "IDENT":
        parser._advance()
        return str(tok.value)
    raise Namel3ssError(
        "Component property values must be text, number, boolean, state paths, or flow names.",
        line=tok.line,
        column=tok.column,
    )


def _can_parse_property_entry(parser) -> bool:
    tok = parser._current()
    if tok.type != "IDENT":
        return False
    if str(tok.value) in _COMPONENT_METADATA_KEYS:
        return False
    if parser.position + 1 >= len(parser.tokens):
        return False
    return parser.tokens[parser.position + 1].type == "COLON"


def _has_continuation_block(parser) -> bool:
    if parser._current().type != "NEWLINE":
        return False
    next_pos = parser.position + 1
    if next_pos >= len(parser.tokens) or parser.tokens[next_pos].type != "INDENT":
        return False
    probe = next_pos + 1
    while probe < len(parser.tokens) and parser.tokens[probe].type == "NEWLINE":
        probe += 1
    if probe >= len(parser.tokens):
        return False
    tok = parser.tokens[probe]
    if tok.type == "IDENT" and str(tok.value) in _COMPONENT_METADATA_KEYS:
        return True
    if tok.type != "IDENT":
        return False
    if probe + 1 >= len(parser.tokens):
        return False
    return parser.tokens[probe + 1].type == "COLON"


__all__ = ["parse_custom_component_item"]

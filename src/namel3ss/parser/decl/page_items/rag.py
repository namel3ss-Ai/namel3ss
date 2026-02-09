from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _parse_param_ref,
    _parse_state_path_value,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_block,
    _validate_visibility_combo,
    _is_param_ref,
)


def parse_citation_chips_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.CitationChipsItem:
    parser._advance()
    _expect_from_keyword(parser, "Citations must use: citations from state.<path>")
    parser._match("IS")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.CitationChipsItem(
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_source_preview_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.SourcePreviewItem:
    parser._advance()
    _expect_from_keyword(parser, "Source previews must use: source_preview from <source_id or state.<path>>")
    parser._match("IS")
    source = _parse_source_reference(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.SourcePreviewItem(
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_trust_indicator_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.TrustIndicatorItem:
    parser._advance()
    _expect_from_keyword(parser, "Trust indicators must use: trust_indicator from state.<path>")
    parser._match("IS")
    source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.TrustIndicatorItem(
        source=source,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_scope_selector_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ScopeSelectorItem:
    parser._advance()
    _expect_from_keyword(parser, "Scope selectors must use: scope_selector from state.<path> active in state.<path>")
    parser._match("IS")
    options_source = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    active_tok = parser._current()
    if active_tok.type != "IDENT" or active_tok.value != "active":
        raise Namel3ssError(
            "Scope selectors must include: active in state.<path>",
            line=active_tok.line,
            column=active_tok.column,
        )
    parser._advance()
    parser._expect("IN", "Expected 'in' after active")
    active = _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.ScopeSelectorItem(
        options_source=options_source,
        active=active,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _expect_from_keyword(parser, message: str) -> None:
    from_tok = parser._current()
    if from_tok.type != "IDENT" or from_tok.value != "from":
        raise Namel3ssError(message, line=from_tok.line, column=from_tok.column)
    parser._advance()


def _parse_source_reference(parser, *, allow_pattern_params: bool):
    tok = parser._current()
    if allow_pattern_params and _is_param_ref(parser):
        return _parse_param_ref(parser)
    if tok.type == "STATE":
        return _parse_state_path_value(parser, allow_pattern_params=allow_pattern_params)
    if tok.type == "STRING":
        parser._advance()
        return ast.Literal(value=str(tok.value), line=tok.line, column=tok.column)
    if tok.type == "IDENT":
        parser._advance()
        return ast.Literal(value=str(tok.value), line=tok.line, column=tok.column)
    raise Namel3ssError(
        "Source previews require a source_id text value or state.<path>.",
        line=tok.line,
        column=tok.column,
    )


__all__ = [
    "parse_citation_chips_item",
    "parse_scope_selector_item",
    "parse_source_preview_item",
    "parse_trust_indicator_item",
]

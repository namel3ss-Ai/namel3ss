from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _parse_optional_string_value,
    _parse_show_when_clause,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _validate_visibility_combo,
)

from .responsive import parse_columns_clause


def parse_section_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.SectionItem:
    parser._advance()
    label = _parse_optional_string_value(parser, allow_pattern_params=allow_pattern_params)
    columns = parse_columns_clause(parser)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after section")
    children, visibility_rule = parse_block(
        parser,
        columns_only=False,
        allow_tabs=False,
        allow_overlays=False,
        allow_pattern_params=allow_pattern_params,
    )
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    item = ast.SectionItem(
        label=label,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )
    if columns is not None:
        item.columns = columns
    return item


def parse_column_item(parser, tok, parse_block, *, allow_pattern_params: bool = False) -> ast.ColumnItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
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
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_divider_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.DividerItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.DividerItem(
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_column_item", "parse_divider_item", "parse_section_item"]

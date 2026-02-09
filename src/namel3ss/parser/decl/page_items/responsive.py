from __future__ import annotations

from decimal import Decimal

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _is_visibility_rule_start,
    _parse_debug_only_clause,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)


def parse_columns_clause(parser) -> list[int] | None:
    tok = parser._current()
    if tok.type != "IDENT" or tok.value != "columns":
        return None
    parser._advance()
    if parser._match("COLON"):
        pass
    else:
        parser._expect("IS", "Expected ':' or 'is' after columns")
    return _parse_integer_list(parser, context="columns")


def parse_grid_item(parser, tok, parse_page_item, *, allow_pattern_params: bool = False) -> ast.GridItem:
    parser._advance()
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after grid")
    parser._expect("NEWLINE", "Expected newline after grid")
    parser._expect("INDENT", "Expected indented grid block")

    columns: list[int] | None = None
    children: list[ast.PageItem] = []
    visibility_rule = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                token = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=token.line,
                    column=token.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue
        parsed_columns = parse_columns_clause(parser)
        if parsed_columns is not None:
            if columns is not None:
                token = parser._current()
                raise Namel3ssError("columns is declared more than once", line=token.line, column=token.column)
            columns = parsed_columns
            parser._match("NEWLINE")
            continue

        parsed = parse_page_item(
            parser,
            allow_tabs=False,
            allow_overlays=False,
            allow_pattern_params=allow_pattern_params,
        )
        if isinstance(parsed, list):
            children.extend(parsed)
        else:
            children.append(parsed)

    parser._expect("DEDENT", "Expected end of grid block")
    if columns is None:
        raise Namel3ssError("Grid block requires columns.", line=tok.line, column=tok.column)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.GridItem(
        columns=columns,
        children=children,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_integer_list(parser, *, context: str) -> list[int]:
    parser._expect("LBRACKET", f"Expected '[' for {context} list")
    values: list[int] = []
    while True:
        tok = parser._expect("NUMBER", f"Expected number in {context} list")
        value = tok.value
        if isinstance(value, Decimal):
            if value != value.to_integral_value():
                raise Namel3ssError(f"{context} values must be integers.", line=tok.line, column=tok.column)
            int_value = int(value)
        else:
            int_value = int(value)
        values.append(int_value)
        if parser._match("COMMA"):
            continue
        break
    parser._expect("RBRACKET", f"Expected ']' after {context} list")
    if not values:
        current = parser._current()
        raise Namel3ssError(f"{context} list cannot be empty.", line=current.line, column=current.column)
    return values


__all__ = ["parse_columns_clause", "parse_grid_item"]

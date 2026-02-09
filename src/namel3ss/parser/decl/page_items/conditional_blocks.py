from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.visibility_expr import parse_visibility_expression


def parse_if_block(parser, tok, parse_page_item, *, allow_pattern_params: bool = False) -> ast.ConditionalBlock:
    parser._advance()
    condition = parse_visibility_expression(parser, allow_pattern_params=allow_pattern_params)
    parser._expect("COLON", "Expected ':' after if condition")
    then_children = _parse_children_block(
        parser,
        parse_page_item,
        allow_pattern_params=allow_pattern_params,
    )
    else_children = None
    if parser._match("NEWLINE"):
        pass
    if parser._current().type == "ELSE":
        parser._advance()
        parser._expect("COLON", "Expected ':' after else")
        else_children = _parse_children_block(
            parser,
            parse_page_item,
            allow_pattern_params=allow_pattern_params,
        )
    return ast.ConditionalBlock(
        condition=condition,
        then_children=then_children,
        else_children=else_children,
        line=tok.line,
        column=tok.column,
    )


def _parse_children_block(parser, parse_page_item, *, allow_pattern_params: bool) -> list[ast.PageItem]:
    parser._expect("NEWLINE", "Expected newline after conditional header")
    parser._expect("INDENT", "Expected indented conditional block")
    items: list[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if parser._current().type == "IDENT" and parser._current().value == "only":
            tok = parser._current()
            raise Namel3ssError(
                "Conditional blocks do not support only-when rules.",
                line=tok.line,
                column=tok.column,
            )
        parsed = parse_page_item(
            parser,
            allow_tabs=False,
            allow_overlays=False,
            allow_pattern_params=allow_pattern_params,
        )
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", "Expected end of conditional block")
    return items


__all__ = ["parse_if_block"]

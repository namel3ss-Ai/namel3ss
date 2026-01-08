from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.parser.decl.page_common import _match_ident_value, _reject_list_transforms
from namel3ss.parser.decl.page_items import parse_page_item


def parse_page(parser) -> ast.PageDecl:
    page_tok = parser._advance()
    name_tok = parser._expect("STRING", "Expected page name string")
    parser._expect("COLON", "Expected ':' after page name")
    requires_expr = None
    if _match_ident_value(parser, "requires"):
        requires_expr = parser._parse_expression()
        _reject_list_transforms(requires_expr)
    parser._expect("NEWLINE", "Expected newline after page header")
    parser._expect("INDENT", "Expected indented page body")
    items: List[ast.PageItem] = []
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        items.append(parse_page_item(parser, allow_tabs=True, allow_overlays=True))
    parser._expect("DEDENT", "Expected end of page body")
    return ast.PageDecl(
        name=name_tok.value,
        items=items,
        requires=requires_expr,
        line=page_tok.line,
        column=page_tok.column,
    )


__all__ = ["parse_page"]

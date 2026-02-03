from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import _match_ident_value, _reject_list_transforms
from namel3ss.parser.decl.page_items import parse_page_item
from namel3ss.parser.decl.page_status import parse_status_block


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
    purpose: str | None = None
    status_block: ast.StatusBlock | None = None
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        tok = parser._current()
        if tok.type == "IDENT" and tok.value == "purpose":
            if purpose is not None:
                raise Namel3ssError("Purpose is already declared for this page", line=tok.line, column=tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after purpose")
            value_tok = parser._expect("STRING", "Expected purpose string")
            purpose = value_tok.value
            parser._match("NEWLINE")
            continue
        if tok.type == "IDENT" and tok.value == "status":
            if status_block is not None:
                raise Namel3ssError("Status is already declared for this page", line=tok.line, column=tok.column)
            status_block = parse_status_block(parser)
            continue
        parsed = parse_page_item(parser, allow_tabs=True, allow_overlays=True)
        if isinstance(parsed, list):
            items.extend(parsed)
        else:
            items.append(parsed)
    parser._expect("DEDENT", "Expected end of page body")
    return ast.PageDecl(
        name=name_tok.value,
        items=items,
        requires=requires_expr,
        purpose=purpose,
        status=status_block,
        line=page_tok.line,
        column=page_tok.column,
    )


__all__ = ["parse_page"]

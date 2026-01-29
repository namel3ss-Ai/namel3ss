from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.decl.page_common import _parse_visibility_clause
from namel3ss.parser.decl.page_media import parse_image_role_block


def parse_image_item(parser, tok) -> ast.ImageItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'image'")
    value_tok = parser._expect("STRING", "Expected image source string")
    visibility = _parse_visibility_clause(parser)
    role = None
    if parser._match("COLON"):
        role = parse_image_role_block(parser, line=tok.line, column=tok.column)
    return ast.ImageItem(src=value_tok.value, alt=None, role=role, visibility=visibility, line=tok.line, column=tok.column)


__all__ = ["parse_image_item"]

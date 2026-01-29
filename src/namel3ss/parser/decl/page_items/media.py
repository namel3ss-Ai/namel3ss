from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.decl.page_common import _parse_string_value, _parse_visibility_clause
from namel3ss.parser.decl.page_media import parse_image_role_block


def parse_image_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ImageItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'image'")
    src = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="image source")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    role = None
    if parser._match("COLON"):
        role = parse_image_role_block(parser, line=tok.line, column=tok.column, allow_pattern_params=allow_pattern_params)
    return ast.ImageItem(src=src, alt=None, role=role, visibility=visibility, line=tok.line, column=tok.column)


__all__ = ["parse_image_item"]

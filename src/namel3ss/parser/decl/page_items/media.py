from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _is_visibility_rule_start,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)


def parse_image_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.ImageItem:
    parser._advance()
    parser._expect("IS", "Expected 'is' after 'image'")
    src = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="image source")
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    role = None
    visibility_rule = None
    if parser._match("COLON"):
        parser._expect("NEWLINE", "Expected newline after image")
        parser._expect("INDENT", "Expected indented image block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            entry_tok = parser._current()
            if _is_visibility_rule_start(parser):
                if visibility_rule is not None:
                    raise Namel3ssError("Visibility blocks may only declare one only-when rule.", line=entry_tok.line, column=entry_tok.column)
                visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
                parser._match("NEWLINE")
                continue
            field = entry_tok.value
            if field != "role":
                raise Namel3ssError("Image blocks may only declare role", line=entry_tok.line, column=entry_tok.column)
            parser._advance()
            parser._expect("IS", "Expected 'is' after role")
            if role is not None:
                raise Namel3ssError("Image role is already declared", line=entry_tok.line, column=entry_tok.column)
            role = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="role")
            parser._match("NEWLINE")
        parser._expect("DEDENT", "Expected end of image block")
        if role is None and visibility_rule is None:
            raise Namel3ssError("Image block has no entries", line=tok.line, column=tok.column)
    else:
        visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.ImageItem(
        src=src,
        alt=None,
        role=role,
        visibility=visibility,
        visibility_rule=visibility_rule,
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_image_item"]

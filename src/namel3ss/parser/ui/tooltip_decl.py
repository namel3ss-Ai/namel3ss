from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _parse_show_when_clause,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _validate_visibility_combo,
)


def parse_tooltip_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.TooltipItem:
    parser._advance()
    text = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="tooltip text")
    if not isinstance(text, str) or not text.strip():
        raise Namel3ssError("tooltip text cannot be empty.", line=tok.line, column=tok.column)

    for_tok = parser._current()
    parser._advance()
    if str(for_tok.value) != "for":
        raise Namel3ssError('Tooltip syntax is: tooltip "<text>" for "<control label>"', line=for_tok.line, column=for_tok.column)
    anchor_label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="tooltip anchor")
    if not isinstance(anchor_label, str) or not anchor_label.strip():
        raise Namel3ssError("Tooltip anchor label cannot be empty.", line=tok.line, column=tok.column)

    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    parser._match("NEWLINE")
    return ast.TooltipItem(
        text=text.strip(),
        anchor_label=anchor_label.strip(),
        collapsed_by_default=True,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


__all__ = ["parse_tooltip_item"]

from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.expr.calls import looks_like_tool_call, parse_tool_call_expr
from namel3ss.parser.expr.common import read_attr_name


def parse_set(parser) -> ast.Set | list[ast.Set]:
    set_tok = parser._advance()
    target = parser._parse_target()
    if parser._match("WITH"):
        return _parse_set_with_block(parser, set_tok, target)
    parser._expect("IS", "Expected 'is' in assignment")
    expr = _parse_set_expression(parser)
    return ast.Set(target=target, expression=expr, line=set_tok.line, column=set_tok.column)


def _parse_set_expression(parser) -> ast.Expression:
    if looks_like_tool_call(parser):
        return parse_tool_call_expr(parser)
    return parser._parse_expression()


def _parse_set_with_block(parser, set_tok, base: ast.Assignable) -> list[ast.Set]:
    if not isinstance(base, ast.StatePath):
        raise Namel3ssError(
            build_guidance_message(
                what="Set block target must be a state path.",
                why="Prefix assignments only work with state paths that can accept dotted fields.",
                fix='Use `set state.<name> with:` and field assignments beneath it.',
                example='set state.order with:\n  order_id is "O-1"\n  customer is "Acme"',
            ),
            line=set_tok.line,
            column=set_tok.column,
        )
    parser._expect("COLON", "Expected ':' after with")
    parser._expect("NEWLINE", "Expected newline after set with block header")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Set block has no assignments.",
                why="Set-with blocks require at least one field assignment.",
                fix="Add one or more field assignments under with:.",
                example='set state.order with:\n  order_id is "O-1"',
            ),
            line=tok.line,
            column=tok.column,
        )

    assignments: list[ast.Set] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        field_tok = parser._current()
        field_parts = _parse_set_with_field(parser)
        field_key = ".".join(field_parts)
        if field_key in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate field '{field_key}' in set block.",
                    why="Each field in a set block must be unique.",
                    fix="Remove the duplicate field assignment.",
                    example='set state.order with:\n  order_id is "O-1"\n  customer is "Acme"',
                ),
                line=field_tok.line,
                column=field_tok.column,
            )
        seen.add(field_key)
        parser._expect("IS", "Expected 'is' after field name")
        expr = _parse_set_expression(parser)
        assignments.append(
            ast.Set(
                target=ast.StatePath(path=base.path + field_parts, line=field_tok.line, column=field_tok.column),
                expression=expr,
                line=field_tok.line,
                column=field_tok.column,
            )
        )
        parser._match("NEWLINE")

    parser._expect("DEDENT", "Expected end of set assignments")
    while parser._match("NEWLINE"):
        pass

    if not assignments:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Set block has no assignments.",
                why="Set-with blocks require at least one field assignment.",
                fix="Add one or more field assignments under with:.",
                example='set state.order with:\n  order_id is "O-1"',
            ),
            line=tok.line,
            column=tok.column,
        )
    return assignments


def _parse_set_with_field(parser) -> list[str]:
    parts = [read_attr_name(parser, context="field name")]
    while parser._match("DOT"):
        parts.append(read_attr_name(parser, context="field name"))
    return parts


__all__ = ["parse_set"]

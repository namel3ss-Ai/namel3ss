from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


LOG_LEVELS = {"debug", "info", "warn", "error"}


def parse_log(parser) -> ast.LogStmt:
    log_tok = parser._advance()
    level_tok = parser._current()
    if level_tok.type != "IDENT":
        raise Namel3ssError(
            build_guidance_message(
                what="Log statement is missing a level.",
                why="Logs must declare a severity level.",
                fix="Add debug, info, warn, or error after log.",
                example='log info "Saved order"',
            ),
            line=level_tok.line,
            column=level_tok.column,
        )
    level = str(level_tok.value).lower()
    if level not in LOG_LEVELS:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Unknown log level '{level_tok.value}'.",
                why="Only debug, info, warn, and error are supported.",
                fix="Use one of the supported log levels.",
                example='log warn "Cache miss"',
            ),
            line=level_tok.line,
            column=level_tok.column,
        )
    parser._advance()
    if parser._current().type in {"NEWLINE", "DEDENT", "EOF"}:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Log statement is missing a message.",
                why="Logs must include a message expression.",
                fix="Provide a message after the level.",
                example='log error "Checkout failed"',
            ),
            line=tok.line,
            column=tok.column,
        )
    message_expr = parser._parse_expression()
    fields_expr = None
    if parser._match("WITH"):
        if parser._current().type in {"NEWLINE", "DEDENT", "EOF"}:
            tok = parser._current()
            raise Namel3ssError(
                build_guidance_message(
                    what="Log fields are missing.",
                    why="The with clause must include a fields object.",
                    fix="Provide a map expression after with.",
                    example='log info "Saved" with map:\n  "id" is order.id',
                ),
                line=tok.line,
                column=tok.column,
            )
        fields_expr = parser._parse_expression()
    return ast.LogStmt(
        level=level,
        message=message_expr,
        fields=fields_expr,
        line=log_tok.line,
        column=log_tok.column,
    )


__all__ = ["parse_log"]

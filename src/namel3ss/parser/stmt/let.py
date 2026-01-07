from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.parser.expr.calls import looks_like_tool_call, parse_tool_call_expr


def parse_let(parser) -> ast.Let | list[ast.Let]:
    let_tok = parser._advance()
    if parser._match("COLON"):
        return _parse_let_block(parser, let_tok)
    name_tok = parser._expect("IDENT", "Expected identifier after 'let'")
    parser._expect("IS", "Expected 'is' in declaration")
    expr = _parse_let_expression(parser)
    constant = False
    if parser._match("CONSTANT"):
        constant = True
    return ast.Let(name=name_tok.value, expression=expr, constant=constant, line=let_tok.line, column=let_tok.column)


def _parse_let_block(parser, let_tok) -> list[ast.Let]:
    parser._expect("NEWLINE", "Expected newline after let:")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Expected an indented block after 'let:'.",
                why="Let blocks require one or more declarations on indented lines.",
                fix="Indent the declarations under let:.",
                example='let:\n  total is 10',
            ),
            line=tok.line,
            column=tok.column,
        )
    entries: list[ast.Let] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        inline_mode = _line_has_inline_commas(parser)
        entries.extend(_parse_let_block_line(parser, seen, inline_mode=inline_mode))
    if not entries:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Let block has no declarations.",
                why="Let blocks require at least one declaration.",
                fix="Add one or more declarations under let:.",
                example='let:\n  total is 10',
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of let block")
    while parser._match("NEWLINE"):
        pass
    return entries


def _parse_let_block_line(parser, seen: set[str], *, inline_mode: bool) -> list[ast.Let]:
    entries: list[ast.Let] = []
    while True:
        entries.append(_parse_let_entry(parser, seen, inline_mode=inline_mode))
        if parser._match("COMMA"):
            comma_tok = parser.tokens[parser.position - 1]
            if parser._current().type in {"NEWLINE", "DEDENT"}:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Expected let entry after ','.",
                        why="Inline let entries must be written as `name is <expr>`.",
                        fix="Add another entry after the comma or remove it.",
                        example='let:\n  a is 1, b is 2',
                    ),
                    line=comma_tok.line,
                    column=comma_tok.column,
                )
            continue
        break
    parser._match("NEWLINE")
    return entries


def _parse_let_entry(parser, seen: set[str], *, inline_mode: bool) -> ast.Let:
    name_tok = parser._expect("IDENT", "Expected identifier in let block")
    parser._expect("IS", "Expected 'is' in declaration")
    if inline_mode:
        _reject_and_separator(parser)
    expr = _parse_let_expression(parser)
    constant = parser._match("CONSTANT")
    if name_tok.value in seen:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Duplicate let name '{name_tok.value}'.",
                why="Each let block entry must use a unique name.",
                fix="Remove or rename the duplicate declaration.",
                example='let:\n  total is 10\n  subtotal is 5',
            ),
            line=name_tok.line,
            column=name_tok.column,
        )
    seen.add(name_tok.value)
    return ast.Let(name=name_tok.value, expression=expr, constant=constant, line=name_tok.line, column=name_tok.column)


def _parse_let_expression(parser) -> ast.Expression:
    if looks_like_tool_call(parser):
        return parse_tool_call_expr(parser)
    return parser._parse_expression()


def _line_has_inline_commas(parser) -> bool:
    depth = 0
    pos = parser.position
    while pos < len(parser.tokens):
        tok = parser.tokens[pos]
        if tok.type in {"NEWLINE", "DEDENT"}:
            break
        if tok.type in {"LPAREN", "LBRACKET"}:
            depth += 1
        elif tok.type in {"RPAREN", "RBRACKET"} and depth > 0:
            depth -= 1
        elif tok.type == "COMMA" and depth == 0:
            return True
        pos += 1
    return False


def _reject_and_separator(parser) -> None:
    depth = 0
    pos = parser.position
    tokens = parser.tokens
    while pos < len(tokens):
        tok = tokens[pos]
        if tok.type in {"NEWLINE", "DEDENT"} and depth == 0:
            break
        if tok.type in {"LPAREN", "LBRACKET"}:
            depth += 1
        elif tok.type in {"RPAREN", "RBRACKET"} and depth > 0:
            depth -= 1
        elif depth == 0:
            if tok.type == "COMMA":
                break
            if tok.type == "AND":
                next_tok = tokens[pos + 1] if pos + 1 < len(tokens) else None
                next_next = tokens[pos + 2] if pos + 2 < len(tokens) else None
                if next_tok and next_next and next_tok.type == "IDENT" and next_next.type == "IS":
                    raise Namel3ssError(
                        build_guidance_message(
                            what="Inline let entries must be separated by commas.",
                            why="`and` is a boolean operator and cannot separate let entries.",
                            fix="Use commas between entries or put each entry on its own line.",
                            example='let:\n  a is 10, b is 5, c is a + b',
                        ),
                        line=tok.line,
                        column=tok.column,
                    )
        pos += 1


__all__ = ["parse_let"]

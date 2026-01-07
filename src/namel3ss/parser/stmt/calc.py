from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.expr.calls import looks_like_tool_call, parse_tool_call_expr


def parse_calc(parser) -> list[ast.Statement]:
    calc_tok = parser._advance()
    parser._expect("COLON", "Expected ':' after calc")
    parser._expect("NEWLINE", "Expected newline after calc:")
    if not parser._match("INDENT"):
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Expected an indented block after 'calc:'.",
                why="Calc blocks require one or more assignments on indented lines.",
                fix="Indent the assignments under calc:.",
                example="calc:\n  total = 10",
            ),
            line=tok.line,
            column=tok.column,
        )
    entries: list[ast.Statement] = []
    seen: set[str] = set()
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        entries.append(_parse_calc_line(parser, seen))
    if not entries:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Calc block has no assignments.",
                why="Calc blocks require at least one assignment.",
                fix="Add one or more assignments under calc:.",
                example="calc:\n  total = 10",
            ),
            line=tok.line,
            column=tok.column,
        )
    parser._expect("DEDENT", "Expected end of calc block")
    while parser._match("NEWLINE"):
        pass
    return entries


def _parse_calc_line(parser, seen: set[str]) -> ast.Statement:
    target, target_tok = _read_calc_target(parser)
    if isinstance(target, str):
        if target in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate calc name '{target}'.",
                    why="Each calc assignment must use a unique name.",
                    fix="Remove or rename the duplicate assignment.",
                    example="calc:\n  total = 10\n  subtotal = 5",
                ),
                line=target_tok.line,
                column=target_tok.column,
            )
        seen.add(target)
    parser._expect("EQUALS", "Expected '=' in calc assignment")
    if parser._current().type in {"NEWLINE", "DEDENT"}:
        tok = parser._current()
        raise Namel3ssError(
            build_guidance_message(
                what="Calc assignment is missing the right-hand expression.",
                why="Calc assignments require an expression after '='.",
                fix="Add an expression to the right-hand side.",
                example="calc:\n  total = 10 + 5",
            ),
            line=tok.line,
            column=tok.column,
        )
    if _line_has_invalid_separator(parser):
        pass
    expr_start = parser.position
    expr = _parse_calc_expression(parser)
    if not _expression_consumed_newline(parser, expr_start):
        if _line_has_extra_tokens(parser):
            tok = parser._current()
            raise Namel3ssError(
                build_guidance_message(
                    what="Calc line contains multiple assignments.",
                    why="Calc lines may only contain a single assignment.",
                    fix="Split the assignments onto separate lines.",
                    example="calc:\n  total = 10\n  subtotal = 5",
                ),
                line=tok.line,
                column=tok.column,
            )
        parser._match("NEWLINE")
    if isinstance(target, ast.StatePath):
        return ast.Set(target=target, expression=expr, line=target_tok.line, column=target_tok.column)
    return ast.Let(name=target, expression=expr, constant=False, line=target_tok.line, column=target_tok.column)


def _read_calc_target(parser) -> tuple[str | ast.StatePath, object]:
    tok = parser._current()
    if tok.type == "STATE":
        path = parser._parse_state_path()
        return path, tok
    if tok.type == "IDENT":
        next_tok = parser.tokens[parser.position + 1] if parser.position + 1 < len(parser.tokens) else None
        if next_tok and next_tok.type == "DOT":
            raise Namel3ssError(
                build_guidance_message(
                    what="Calc assignments may only target local names or state paths.",
                    why="Only local variables or state.<name> are valid calc assignment targets.",
                    fix="Use a local name or a state path.",
                    example="calc:\n  total = 10\n  state.total = total",
                ),
                line=tok.line,
                column=tok.column,
            )
        parser._advance()
        return tok.value, tok
    if tok.type == "INPUT":
        raise Namel3ssError(
            build_guidance_message(
                what="Calc assignments may only target local names or state paths.",
                why="Only local variables or state.<name> are valid calc assignment targets.",
                fix="Use a local name or a state path.",
                example="calc:\n  total = 10\n  state.total = total",
            ),
            line=tok.line,
            column=tok.column,
        )
    if isinstance(tok.value, str) and is_keyword(tok.value):
        raise Namel3ssError(
            build_guidance_message(
                what=f"'{tok.value}' is a reserved keyword.",
                why="Calc assignments require keyword-safe identifiers.",
                fix="Choose a different name.",
                example="calc:\n  total = 10",
            ),
            line=tok.line,
            column=tok.column,
        )
    if tok.type == "IDENT" or tok.type == "DOT":
        raise Namel3ssError(
            build_guidance_message(
                what="Calc assignments may only target local names or state paths.",
                why="Only local variables or state.<name> are valid calc assignment targets.",
                fix="Use a local name or a state path.",
                example="calc:\n  total = 10\n  state.total = total",
            ),
            line=tok.line,
            column=tok.column,
        )
    raise Namel3ssError("Expected identifier in calc assignment", line=tok.line, column=tok.column)


def _parse_calc_expression(parser) -> ast.Expression:
    if looks_like_tool_call(parser):
        return parse_tool_call_expr(parser)
    return parser._parse_expression()


def _line_has_invalid_separator(parser) -> bool:
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
                raise Namel3ssError(
                    build_guidance_message(
                        what="Calc lines cannot contain commas.",
                        why="Calc lines may only contain a single assignment.",
                        fix="Split the assignments onto separate lines.",
                        example="calc:\n  total = 10\n  subtotal = 5",
                    ),
                    line=tok.line,
                    column=tok.column,
                )
            if tok.type == "AND":
                next_tok = tokens[pos + 1] if pos + 1 < len(tokens) else None
                next_next = tokens[pos + 2] if pos + 2 < len(tokens) else None
                if next_tok and next_next and next_tok.type == "IDENT" and next_next.type == "EQUALS":
                    raise Namel3ssError(
                        build_guidance_message(
                            what="Calc lines cannot contain multiple assignments.",
                            why="Calc lines may only contain a single assignment.",
                            fix="Split the assignments onto separate lines.",
                            example="calc:\n  total = 10\n  subtotal = 5",
                        ),
                        line=tok.line,
                        column=tok.column,
                    )
        pos += 1
    return False


def _line_has_extra_tokens(parser) -> bool:
    depth = 0
    pos = parser.position
    tokens = parser.tokens
    while pos < len(tokens):
        tok = tokens[pos]
        if tok.type in {"NEWLINE", "DEDENT"} and depth == 0:
            return False
        if tok.type in {"LPAREN", "LBRACKET"}:
            depth += 1
        elif tok.type in {"RPAREN", "RBRACKET"} and depth > 0:
            depth -= 1
        elif depth == 0 and tok.type == "EQUALS":
            return True
        pos += 1
    return False


def _expression_consumed_newline(parser, start: int) -> bool:
    for tok in parser.tokens[start: parser.position]:
        if tok.type == "NEWLINE":
            return True
    return False


__all__ = ["parse_calc"]

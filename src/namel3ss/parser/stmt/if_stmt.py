from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def parse_if(parser) -> ast.If:
    if_tok = parser._advance()
    condition = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after condition")
    parser._expect("NEWLINE", "Expected newline after condition")
    if parser._current().type != "INDENT":
        tok = parser._current()
        raise Namel3ssError(_indentation_message("if"), line=tok.line, column=tok.column)
    parser._advance()
    then_body = parser._parse_statements(until={"DEDENT"})
    parser._expect("DEDENT", "Expected block end")
    else_body: list[ast.Statement] = []
    while parser._match("NEWLINE"):
        pass
    if parser._match("ELSE"):
        parser._expect("COLON", "Expected ':' after else")
        parser._expect("NEWLINE", "Expected newline after else")
        if parser._current().type != "INDENT":
            tok = parser._current()
            raise Namel3ssError(_indentation_message("else"), line=tok.line, column=tok.column)
        parser._advance()
        else_body = parser._parse_statements(until={"DEDENT"})
        parser._expect("DEDENT", "Expected block end")
        while parser._match("NEWLINE"):
            pass
    return ast.If(
        condition=condition,
        then_body=then_body,
        else_body=else_body,
        line=if_tok.line,
        column=if_tok.column,
    )


def _indentation_message(keyword: str) -> str:
    return build_guidance_message(
        what=f"Expected an indented block after '{keyword}'.",
        why="Blocks in namel3ss are defined by indentation after a ':' header.",
        fix="Indent the statements under the block (two spaces is typical).",
        example='if total is greater than 10:\n  set state.tier is "pro"',
    )


__all__ = ["parse_if"]

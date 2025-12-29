from __future__ import annotations

from typing import List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError


def parse_match(parser) -> ast.Match:
    match_tok = parser._advance()
    expr = parser._parse_expression()
    parser._expect("COLON", "Expected ':' after match expression")
    parser._expect("NEWLINE", "Expected newline after match header")
    parser._expect("INDENT", "Expected indented match body")
    parser._expect("WITH", "Expected 'with' inside match")
    parser._expect("COLON", "Expected ':' after 'with'")
    parser._expect("NEWLINE", "Expected newline after 'with:'")
    parser._expect("INDENT", "Expected indented match cases")
    cases: List[ast.MatchCase] = []
    otherwise_body: List[ast.Statement] | None = None
    while parser._current().type not in {"DEDENT"}:
        if parser._match("WHEN"):
            pattern_expr = parser._parse_expression()
            parser._validate_match_pattern(pattern_expr)
            parser._expect("COLON", "Expected ':' after when pattern")
            case_body = parser._parse_block()
            if otherwise_body is not None:
                raise Namel3ssError(
                    "Unreachable case after otherwise",
                    line=pattern_expr.line,
                    column=pattern_expr.column,
                )
            cases.append(
                ast.MatchCase(
                    pattern=pattern_expr,
                    body=case_body,
                    line=pattern_expr.line,
                    column=pattern_expr.column,
                )
            )
            continue
        if parser._match("OTHERWISE"):
            if otherwise_body is not None:
                tok = parser.tokens[parser.position - 1]
                raise Namel3ssError("Duplicate otherwise in match", line=tok.line, column=tok.column)
            parser._expect("COLON", "Expected ':' after otherwise")
            otherwise_body = parser._parse_block()
            continue
        tok = parser._current()
        raise Namel3ssError("Expected 'when' or 'otherwise' in match", line=tok.line, column=tok.column)
    parser._expect("DEDENT", "Expected end of match cases")
    parser._expect("DEDENT", "Expected end of match block")
    while parser._match("NEWLINE"):
        pass
    if not cases and otherwise_body is None:
        raise Namel3ssError("Match must have at least one case", line=match_tok.line, column=match_tok.column)
    return ast.Match(expression=expr, cases=cases, otherwise=otherwise_body, line=match_tok.line, column=match_tok.column)


__all__ = ["parse_match"]

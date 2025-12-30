from __future__ import annotations

from typing import List, Set

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.grammar_table import select_statement_rule


def parse_statement(parser) -> ast.Statement | list[ast.Statement]:
    tok = parser._current()
    rule = select_statement_rule(parser)
    if rule is not None:
        return rule.parse(parser)
    if tok.type == "RUN":
        raise Namel3ssError("Expected 'agent' or 'agents' after run", line=tok.line, column=tok.column)
    raise Namel3ssError(f"Unexpected token '{tok.type}' in statement", line=tok.line, column=tok.column)


def parse_statements(parser, until: Set[str]) -> List[ast.Statement]:
    statements: List[ast.Statement] = []
    while parser._current().type not in until:
        if parser._match("NEWLINE"):
            continue
        stmt = parser._parse_statement()
        if isinstance(stmt, list):
            statements.extend(stmt)
        else:
            statements.append(stmt)
    return statements


def parse_block(parser) -> List[ast.Statement]:
    parser._expect("NEWLINE", "Expected newline before block")
    parser._expect("INDENT", "Expected indented block")
    stmts = parse_statements(parser, until={"DEDENT"})
    parser._expect("DEDENT", "Expected end of block")
    while parser._match("NEWLINE"):
        pass
    return stmts


def parse_target(parser) -> ast.Assignable:
    tok = parser._current()
    if tok.type == "STATE":
        return parser._parse_state_path()
    if tok.type == "IDENT":
        name_tok = parser._advance()
        return ast.VarReference(name=name_tok.value, line=name_tok.line, column=name_tok.column)
    raise Namel3ssError("Expected assignment target", line=tok.line, column=tok.column)


def validate_match_pattern(parser, pattern: ast.Expression) -> None:
    if isinstance(pattern, (ast.Literal, ast.VarReference, ast.StatePath)):
        return
    raise Namel3ssError("Match patterns must be literal or identifier", line=pattern.line, column=pattern.column)


__all__ = [
    "parse_block",
    "parse_statement",
    "parse_statements",
    "parse_target",
    "validate_match_pattern",
]

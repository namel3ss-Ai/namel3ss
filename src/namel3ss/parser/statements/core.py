from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.agent import parse_run_agent_stmt, parse_run_agents_parallel
from namel3ss.parser.ai import parse_ask_stmt
from namel3ss.parser.statements.control_flow import (
    parse_for_each,
    parse_if,
    parse_match,
    parse_repeat,
    parse_return,
    parse_try,
)
from namel3ss.parser.statements.data import parse_find, parse_save
from namel3ss.parser.statements.letset import parse_let, parse_set


def parse_statement(parser) -> ast.Statement:
    tok = parser._current()
    if tok.type == "LET":
        return parse_let(parser)
    if tok.type == "SET":
        return parse_set(parser)
    if tok.type == "IF":
        return parse_if(parser)
    if tok.type == "RETURN":
        return parse_return(parser)
    if tok.type == "ASK":
        return parse_ask_stmt(parser)
    if tok.type == "RUN":
        next_type = parser.tokens[parser.position + 1].type
        if next_type == "AGENT":
            return parse_run_agent_stmt(parser)
        if next_type == "AGENTS":
            return parse_run_agents_parallel(parser)
        raise Namel3ssError("Expected 'agent' or 'agents' after run", line=tok.line, column=tok.column)
    if tok.type == "REPEAT":
        return parse_repeat(parser)
    if tok.type == "FOR":
        return parse_for_each(parser)
    if tok.type == "MATCH":
        return parse_match(parser)
    if tok.type == "TRY":
        return parse_try(parser)
    if tok.type == "SAVE":
        return parse_save(parser)
    if tok.type == "FIND":
        return parse_find(parser)
    raise Namel3ssError(f"Unexpected token '{tok.type}' in statement", line=tok.line, column=tok.column)


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

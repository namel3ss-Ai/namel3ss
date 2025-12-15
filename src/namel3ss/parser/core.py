from __future__ import annotations

from typing import List, Set

from namel3ss.ast import nodes as ast
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.tokens import Token
from namel3ss.parser import tokens as token_ops
from namel3ss.parser.constraints import parse_field_constraint
from namel3ss.parser.expressions import (
    parse_comparison,
    parse_expression,
    parse_not,
    parse_or,
    parse_primary,
    parse_state_path,
)
from namel3ss.parser.expressions import parse_and as parse_and_expr
from namel3ss.parser.flow import parse_block, parse_flow, parse_statements
from namel3ss.parser.pages import parse_page, parse_page_item
from namel3ss.parser.program import parse_program
from namel3ss.parser.records import parse_record, parse_record_fields, type_from_token
from namel3ss.parser.statements import (
    parse_find,
    parse_for_each,
    parse_if,
    parse_let,
    parse_match,
    parse_repeat,
    parse_return,
    parse_save,
    parse_set,
    parse_statement,
    parse_target,
    parse_try,
    validate_match_pattern,
)


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.position = 0

    @classmethod
    def parse(cls, source: str) -> ast.Program:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = cls(tokens)
        program = parser._parse_program()
        parser._expect("EOF")
        return program

    # Token helpers
    def _current(self) -> Token:
        return token_ops.current(self)

    def _advance(self) -> Token:
        return token_ops.advance(self)

    def _match(self, *types: str) -> bool:
        return token_ops.match(self, *types)

    def _expect(self, token_type: str, message=None) -> Token:
        return token_ops.expect(self, token_type, message)

    # Program level
    def _parse_program(self) -> ast.Program:
        return parse_program(self)

    # Flow and blocks
    def _parse_flow(self) -> ast.Flow:
        return parse_flow(self)

    def _parse_statements(self, until: Set[str]) -> List[ast.Statement]:
        return parse_statements(self, until)

    def _parse_block(self) -> List[ast.Statement]:
        return parse_block(self)

    # Statements
    def _parse_statement(self) -> ast.Statement:
        return parse_statement(self)

    def _parse_let(self) -> ast.Let:
        return parse_let(self)

    def _parse_set(self) -> ast.Set:
        return parse_set(self)

    def _parse_if(self) -> ast.If:
        return parse_if(self)

    def _parse_return(self) -> ast.Return:
        return parse_return(self)

    def _parse_repeat(self) -> ast.Repeat:
        return parse_repeat(self)

    def _parse_for_each(self) -> ast.ForEach:
        return parse_for_each(self)

    def _parse_match(self) -> ast.Match:
        return parse_match(self)

    def _parse_try(self) -> ast.TryCatch:
        return parse_try(self)

    def _parse_save(self) -> ast.Save:
        return parse_save(self)

    def _parse_find(self) -> ast.Find:
        return parse_find(self)

    def _parse_target(self) -> ast.Assignable:
        return parse_target(self)

    def _validate_match_pattern(self, pattern: ast.Expression) -> None:
        return validate_match_pattern(self, pattern)

    # Expressions
    def _parse_expression(self) -> ast.Expression:
        return parse_expression(self)

    def _parse_or(self) -> ast.Expression:
        return parse_or(self)

    def _parse_and(self) -> ast.Expression:
        return parse_and_expr(self)

    def _parse_not(self) -> ast.Expression:
        return parse_not(self)

    def _parse_comparison(self) -> ast.Expression:
        return parse_comparison(self)

    def _parse_primary(self) -> ast.Expression:
        return parse_primary(self)

    def _parse_state_path(self) -> ast.StatePath:
        return parse_state_path(self)

    # Records and constraints
    def _parse_record(self) -> ast.RecordDecl:
        return parse_record(self)

    def _parse_record_fields(self) -> List[ast.FieldDecl]:
        return parse_record_fields(self)

    def _parse_field_constraint(self) -> ast.FieldConstraint:
        return parse_field_constraint(self)

    @staticmethod
    def _type_from_token(tok: Token) -> str:
        return type_from_token(tok)

    # Pages
    def _parse_page(self) -> ast.PageDecl:
        return parse_page(self)

    def _parse_page_item(self) -> ast.PageItem:
        return parse_page_item(self)


def parse(source: str) -> ast.Program:
    return Parser.parse(source)

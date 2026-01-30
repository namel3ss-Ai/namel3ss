from __future__ import annotations

from typing import List, Set

from namel3ss.ast import nodes as ast
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.tokens import Token
from namel3ss.parser.core.stream import TokenStream
from namel3ss.parser.core import tokens as token_ops
from namel3ss.parser.decl.constraints import parse_field_constraint
from namel3ss.parser.decl.flow import parse_flow
from namel3ss.parser.decl.page import parse_page, parse_page_item
from namel3ss.parser.decl.record import parse_record, parse_record_fields, type_from_token
from namel3ss.parser.expr.comparisons import parse_comparison
from namel3ss.parser.expr.ops import (
    parse_additive,
    parse_and,
    parse_expression,
    parse_not,
    parse_or,
    parse_primary,
)
from namel3ss.parser.expr.statepath import parse_state_path
from namel3ss.parser.parse_program import parse_program
from namel3ss.parser.sugar.lower import lower_program as lower_sugar_program
from namel3ss.parser.stmt.common import (
    parse_block,
    parse_statement,
    parse_statements,
    parse_target,
    validate_match_pattern,
)
from namel3ss.parser.stmt.create import parse_create
from namel3ss.parser.stmt.find import parse_find
from namel3ss.parser.stmt.foreach import parse_for_each
from namel3ss.parser.stmt.if_stmt import parse_if
from namel3ss.parser.stmt.let import parse_let
from namel3ss.parser.stmt.match import parse_match
from namel3ss.parser.stmt.repeat import parse_repeat
from namel3ss.parser.stmt.return_stmt import parse_return
from namel3ss.parser.stmt.save import parse_save
from namel3ss.parser.stmt.set import parse_set
from namel3ss.parser.stmt.trycatch import parse_try


class Parser(TokenStream):
    def __init__(
        self,
        tokens: List[Token],
        allow_legacy_type_aliases: bool = True,
        *,
        allow_capsule: bool = False,
        require_spec: bool = True,
    ) -> None:
        super().__init__(tokens=tokens)
        self.allow_legacy_type_aliases = allow_legacy_type_aliases
        self.allow_capsule = allow_capsule
        self.require_spec = require_spec

    @classmethod
    def parse(
        cls,
        source: str,
        allow_legacy_type_aliases: bool = True,
        *,
        allow_capsule: bool = False,
        require_spec: bool = True,
        lower_sugar: bool = True,
    ) -> ast.Program:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = cls(
            tokens,
            allow_legacy_type_aliases=allow_legacy_type_aliases,
            allow_capsule=allow_capsule,
            require_spec=require_spec,
        )
        program = parser._parse_program()
        if lower_sugar:
            program = lower_sugar_program(program)
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
    def _parse_statement(self) -> ast.Statement | list[ast.Statement]:
        return parse_statement(self)

    def _parse_let(self) -> ast.Let | list[ast.Let]:
        return parse_let(self)

    def _parse_set(self) -> ast.Set | list[ast.Set]:
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

    def _parse_create(self) -> ast.Create:
        return parse_create(self)

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
        return parse_and(self)

    def _parse_not(self) -> ast.Expression:
        return parse_not(self)

    def _parse_comparison(self) -> ast.Expression:
        return parse_comparison(self)

    def _parse_additive(self) -> ast.Expression:
        return parse_additive(self)

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


def parse(
    source: str,
    allow_legacy_type_aliases: bool = True,
    *,
    allow_capsule: bool = False,
    require_spec: bool = True,
    lower_sugar: bool = True,
) -> ast.Program:
    return Parser.parse(
        source,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
        require_spec=require_spec,
        lower_sugar=lower_sugar,
    )


__all__ = ["Parser", "parse"]

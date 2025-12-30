from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TopLevelRule:
    name: str
    token_type: str
    parse: Callable
    token_value: str | None = None

    def matches(self, parser) -> bool:
        tok = parser._current()
        if tok.type != self.token_type:
            return False
        if self.token_value is not None and tok.value != self.token_value:
            return False
        return True


@dataclass(frozen=True)
class StatementRule:
    name: str
    token_type: str
    parse: Callable
    token_value: str | None = None
    predicate: Callable | None = None

    def matches(self, parser) -> bool:
        tok = parser._current()
        if tok.type != self.token_type:
            return False
        if self.token_value is not None and tok.value != self.token_value:
            return False
        if self.predicate is not None and not self.predicate(parser):
            return False
        return True


@dataclass(frozen=True)
class ExpressionRule:
    name: str
    token_type: str
    parse: Callable

    def matches(self, parser) -> bool:
        return parser._current().type == self.token_type


def top_level_rules() -> tuple[TopLevelRule, ...]:
    from namel3ss.parser.decl.ai import parse_ai_decl
    from namel3ss.parser.decl.agent import parse_agent_decl
    from namel3ss.parser.decl.app import parse_app
    from namel3ss.parser.decl.capsule import parse_capsule_decl
    from namel3ss.parser.decl.flow import parse_flow
    from namel3ss.parser.decl.function import parse_function_decl
    from namel3ss.parser.decl.identity import parse_identity
    from namel3ss.parser.decl.page import parse_page
    from namel3ss.parser.decl.record import parse_record
    from namel3ss.parser.decl.spec import parse_spec_decl
    from namel3ss.parser.decl.tool import parse_tool
    from namel3ss.parser.decl.use import parse_use_decl

    return (
        TopLevelRule("spec", "SPEC", parse_spec_decl),
        TopLevelRule("function", "IDENT", parse_function_decl, token_value="define"),
        TopLevelRule("use", "IDENT", parse_use_decl, token_value="use"),
        TopLevelRule("capsule", "IDENT", parse_capsule_decl, token_value="capsule"),
        TopLevelRule("identity", "IDENT", parse_identity, token_value="identity"),
        TopLevelRule("app", "APP", parse_app),
        TopLevelRule("tool", "TOOL", parse_tool),
        TopLevelRule("agent", "AGENT", parse_agent_decl),
        TopLevelRule("ai", "AI", parse_ai_decl),
        TopLevelRule("record", "RECORD", parse_record),
        TopLevelRule("flow", "FLOW", parse_flow),
        TopLevelRule("page", "PAGE", parse_page),
    )


def statement_rules() -> tuple[StatementRule, ...]:
    from namel3ss.parser.stmt.ask_ai import parse_ask_stmt
    from namel3ss.parser.stmt.create import parse_create
    from namel3ss.parser.stmt.find import parse_find
    from namel3ss.parser.stmt.foreach import parse_for_each
    from namel3ss.parser.stmt.if_stmt import parse_if
    from namel3ss.parser.stmt.let import parse_let
    from namel3ss.parser.stmt.match import parse_match
    from namel3ss.parser.stmt.parallel import parse_parallel
    from namel3ss.parser.stmt.repeat import parse_repeat
    from namel3ss.parser.stmt.return_stmt import parse_return
    from namel3ss.parser.stmt.run_agent import parse_run_agent_stmt, parse_run_agents_parallel
    from namel3ss.parser.stmt.save import parse_save
    from namel3ss.parser.stmt.set import parse_set
    from namel3ss.parser.stmt.theme import parse_set_theme
    from namel3ss.parser.stmt.update import parse_update
    from namel3ss.parser.stmt.delete import parse_delete
    from namel3ss.parser.stmt.trycatch import parse_try

    return (
        StatementRule("let", "LET", parse_let),
        StatementRule("set_theme", "SET", parse_set_theme, predicate=_is_set_theme),
        StatementRule("set", "SET", parse_set),
        StatementRule("if", "IF", parse_if),
        StatementRule("return", "RETURN", parse_return),
        StatementRule("ask", "ASK", parse_ask_stmt),
        StatementRule("parallel", "PARALLEL", parse_parallel),
        StatementRule("run_agents_parallel", "RUN", parse_run_agents_parallel, predicate=_is_run_agents_parallel),
        StatementRule("run_agent", "RUN", parse_run_agent_stmt, predicate=_is_run_agent),
        StatementRule("repeat", "REPEAT", parse_repeat),
        StatementRule("for_each", "FOR", parse_for_each),
        StatementRule("match", "MATCH", parse_match),
        StatementRule("try", "TRY", parse_try),
        StatementRule("save", "SAVE", parse_save),
        StatementRule("create", "CREATE", parse_create),
        StatementRule("find", "FIND", parse_find),
        StatementRule("update", "IDENT", parse_update, token_value="update"),
        StatementRule("delete", "IDENT", parse_delete, token_value="delete"),
    )


def expression_rules() -> tuple[ExpressionRule, ...]:
    from namel3ss.parser.expr.calls import parse_ask_expression, parse_call_function_expr
    from namel3ss.parser.expr.literals import (
        parse_boolean_literal,
        parse_null_literal,
        parse_number_literal,
        parse_string_literal,
    )
    from namel3ss.parser.expr.ops import parse_grouped_expression
    from namel3ss.parser.expr.refs import parse_reference_expr
    from namel3ss.parser.expr.statepath import parse_state_path

    return (
        ExpressionRule("number", "NUMBER", parse_number_literal),
        ExpressionRule("string", "STRING", parse_string_literal),
        ExpressionRule("boolean", "BOOLEAN", parse_boolean_literal),
        ExpressionRule("null", "NULL", parse_null_literal),
        ExpressionRule("identifier", "IDENT", parse_reference_expr),
        ExpressionRule("input", "INPUT", parse_reference_expr),
        ExpressionRule("state", "STATE", parse_state_path),
        ExpressionRule("grouped", "LPAREN", parse_grouped_expression),
        ExpressionRule("call", "CALL", parse_call_function_expr),
        ExpressionRule("ask", "ASK", parse_ask_expression),
    )


def select_top_level_rule(parser) -> TopLevelRule | None:
    for rule in top_level_rules():
        if rule.matches(parser):
            return rule
    return None


def select_statement_rule(parser) -> StatementRule | None:
    for rule in statement_rules():
        if rule.matches(parser):
            return rule
    return None


def select_expression_rule(parser) -> ExpressionRule | None:
    for rule in expression_rules():
        if rule.matches(parser):
            return rule
    return None


def _is_set_theme(parser) -> bool:
    next_type = parser.tokens[parser.position + 1].type if parser.position + 1 < len(parser.tokens) else None
    return next_type == "THEME"


def _is_run_agent(parser) -> bool:
    next_type = parser.tokens[parser.position + 1].type if parser.position + 1 < len(parser.tokens) else None
    return next_type == "AGENT"


def _is_run_agents_parallel(parser) -> bool:
    next_type = parser.tokens[parser.position + 1].type if parser.position + 1 < len(parser.tokens) else None
    return next_type == "AGENTS"


__all__ = [
    "ExpressionRule",
    "StatementRule",
    "TopLevelRule",
    "expression_rules",
    "select_expression_rule",
    "select_statement_rule",
    "select_top_level_rule",
    "statement_rules",
    "top_level_rules",
]

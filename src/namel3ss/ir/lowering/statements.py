from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.expressions import _lower_assignable, _lower_expression
from namel3ss.ir.model.agents import ParallelAgentEntry, RunAgentStmt, RunAgentsParallelStmt
from namel3ss.ir.model.ai import AskAIStmt
from namel3ss.ir.model.statements import (
    Find,
    ForEach,
    If,
    Let,
    Match,
    MatchCase,
    Repeat,
    Return,
    Save,
    Set,
    TryCatch,
)
from namel3ss.ir.model.statements import Statement as IRStatement


def _lower_statement(stmt: ast.Statement, agents) -> IRStatement:
    if isinstance(stmt, ast.Let):
        return Let(
            name=stmt.name,
            expression=_lower_expression(stmt.expression),
            constant=stmt.constant,
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.Set):
        return Set(
            target=_lower_assignable(stmt.target),
            expression=_lower_expression(stmt.expression),
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.If):
        return If(
            condition=_lower_expression(stmt.condition),
            then_body=[_lower_statement(s, agents) for s in stmt.then_body],
            else_body=[_lower_statement(s, agents) for s in stmt.else_body],
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.Return):
        return Return(
            expression=_lower_expression(stmt.expression),
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.Repeat):
        return Repeat(
            count=_lower_expression(stmt.count),
            body=[_lower_statement(s, agents) for s in stmt.body],
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.ForEach):
        return ForEach(
            name=stmt.name,
            iterable=_lower_expression(stmt.iterable),
            body=[_lower_statement(s, agents) for s in stmt.body],
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.AskAIStmt):
        return AskAIStmt(
            ai_name=stmt.ai_name,
            input_expr=_lower_expression(stmt.input_expr),
            target=stmt.target,
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.Match):
        return Match(
            expression=_lower_expression(stmt.expression),
            cases=[
                MatchCase(
                    pattern=_lower_expression(case.pattern),
                    body=[_lower_statement(s, agents) for s in case.body],
                    line=case.line,
                    column=case.column,
                )
                for case in stmt.cases
            ],
            otherwise=[_lower_statement(s, agents) for s in stmt.otherwise] if stmt.otherwise is not None else None,
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.TryCatch):
        return TryCatch(
            try_body=[_lower_statement(s, agents) for s in stmt.try_body],
            catch_var=stmt.catch_var,
            catch_body=[_lower_statement(s, agents) for s in stmt.catch_body],
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.Save):
        return Save(record_name=stmt.record_name, line=stmt.line, column=stmt.column)
    if isinstance(stmt, ast.Find):
        return Find(record_name=stmt.record_name, predicate=_lower_expression(stmt.predicate), line=stmt.line, column=stmt.column)
    if isinstance(stmt, ast.RunAgentStmt):
        return RunAgentStmt(
            agent_name=stmt.agent_name,
            input_expr=_lower_expression(stmt.input_expr),
            target=stmt.target,
            line=stmt.line,
            column=stmt.column,
        )
    if isinstance(stmt, ast.RunAgentsParallelStmt):
        return RunAgentsParallelStmt(
            entries=[
                ParallelAgentEntry(agent_name=e.agent_name, input_expr=_lower_expression(e.input_expr), line=e.line, column=e.column)
                for e in stmt.entries
            ],
            target=stmt.target,
            line=stmt.line,
            column=stmt.column,
        )
    raise TypeError(f"Unhandled statement type: {type(stmt)}")

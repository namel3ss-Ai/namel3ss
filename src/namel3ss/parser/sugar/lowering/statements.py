from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar import grammar as sugar
from namel3ss.parser.sugar.lowering.expressions import _lower_expression
from namel3ss.parser.sugar.lowering.sugar_statements import (
    _lower_attempt_blocked,
    _lower_compute_hash,
    _lower_increment_metric,
    _lower_plan,
    _lower_policy_violation,
    _lower_record_output,
    _lower_review,
    _lower_start_run,
    _lower_timeline,
)


def _lower_statements(statements: list[ast.Statement]) -> list[ast.Statement]:
    lowered: list[ast.Statement] = []
    for stmt in statements:
        lowered.extend(_lower_statement(stmt))
    return lowered


def _lower_statement(stmt: ast.Statement) -> list[ast.Statement]:
    if isinstance(stmt, sugar.StartRunStmt):
        return _lower_start_run(stmt)
    if isinstance(stmt, sugar.PlanWithAgentStmt):
        return [_lower_plan(stmt)]
    if isinstance(stmt, sugar.ReviewParallelStmt):
        return [_lower_review(stmt)]
    if isinstance(stmt, sugar.TimelineShowStmt):
        return _lower_timeline(stmt)
    if isinstance(stmt, sugar.ComputeOutputHashStmt):
        return [_lower_compute_hash(stmt)]
    if isinstance(stmt, sugar.RecordFinalOutputStmt):
        return _lower_record_output(stmt)
    if isinstance(stmt, sugar.IncrementMetricStmt):
        return _lower_increment_metric(stmt)
    if isinstance(stmt, sugar.RecordPolicyViolationStmt):
        return _lower_policy_violation(stmt)
    if isinstance(stmt, sugar.AttemptBlockedToolStmt):
        return _lower_attempt_blocked(stmt)

    if isinstance(stmt, ast.Let):
        return [ast.Let(name=stmt.name, expression=_lower_expression(stmt.expression), constant=stmt.constant, line=stmt.line, column=stmt.column)]
    if isinstance(stmt, ast.Set):
        return [ast.Set(target=stmt.target, expression=_lower_expression(stmt.expression), line=stmt.line, column=stmt.column)]
    if isinstance(stmt, ast.If):
        return [
            ast.If(
                condition=_lower_expression(stmt.condition),
                then_body=_lower_statements(stmt.then_body),
                else_body=_lower_statements(stmt.else_body),
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.Return):
        return [ast.Return(expression=_lower_expression(stmt.expression), line=stmt.line, column=stmt.column)]
    if isinstance(stmt, ast.AskAIStmt):
        return [
            ast.AskAIStmt(
                ai_name=stmt.ai_name,
                input_expr=_lower_expression(stmt.input_expr),
                target=stmt.target,
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.RunAgentStmt):
        return [
            ast.RunAgentStmt(
                agent_name=stmt.agent_name,
                input_expr=_lower_expression(stmt.input_expr),
                target=stmt.target,
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.RunAgentsParallelStmt):
        entries = [
            ast.ParallelAgentEntry(
                agent_name=entry.agent_name,
                input_expr=_lower_expression(entry.input_expr),
                line=entry.line,
                column=entry.column,
            )
            for entry in stmt.entries
        ]
        merge = stmt.merge
        if merge:
            merge = ast.AgentMergePolicy(
                policy=merge.policy,
                require_keys=merge.require_keys,
                require_non_empty=merge.require_non_empty,
                score_key=merge.score_key,
                score_rule=merge.score_rule,
                min_consensus=merge.min_consensus,
                consensus_key=merge.consensus_key,
                line=merge.line,
                column=merge.column,
            )
        return [
            ast.RunAgentsParallelStmt(
                entries=entries,
                target=stmt.target,
                merge=merge,
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.ParallelBlock):
        tasks = [
            ast.ParallelTask(
                name=task.name,
                body=_lower_statements(task.body),
                line=task.line,
                column=task.column,
            )
            for task in stmt.tasks
        ]
        return [ast.ParallelBlock(tasks=tasks, line=stmt.line, column=stmt.column)]
    if isinstance(stmt, ast.Repeat):
        return [
            ast.Repeat(
                count=_lower_expression(stmt.count),
                body=_lower_statements(stmt.body),
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.RepeatWhile):
        return [
            ast.RepeatWhile(
                condition=_lower_expression(stmt.condition),
                limit=stmt.limit,
                body=_lower_statements(stmt.body),
                line=stmt.line,
                column=stmt.column,
                limit_line=stmt.limit_line,
                limit_column=stmt.limit_column,
            )
        ]
    if isinstance(stmt, ast.ForEach):
        return [
            ast.ForEach(
                name=stmt.name,
                iterable=_lower_expression(stmt.iterable),
                body=_lower_statements(stmt.body),
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.Match):
        cases = [
            ast.MatchCase(
                pattern=_lower_expression(case.pattern),
                body=_lower_statements(case.body),
                line=case.line,
                column=case.column,
            )
            for case in stmt.cases
        ]
        otherwise = _lower_statements(stmt.otherwise) if stmt.otherwise is not None else None
        return [
            ast.Match(
                expression=_lower_expression(stmt.expression),
                cases=cases,
                otherwise=otherwise,
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.TryCatch):
        return [
            ast.TryCatch(
                try_body=_lower_statements(stmt.try_body),
                catch_var=stmt.catch_var,
                catch_body=_lower_statements(stmt.catch_body),
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.Save):
        return [stmt]
    if isinstance(stmt, ast.Create):
        return [
            ast.Create(
                record_name=stmt.record_name,
                values=_lower_expression(stmt.values),
                target=stmt.target,
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.Find):
        return [ast.Find(record_name=stmt.record_name, predicate=_lower_expression(stmt.predicate), line=stmt.line, column=stmt.column)]
    if isinstance(stmt, ast.Update):
        updates = [
            ast.UpdateField(
                name=update.name,
                expression=_lower_expression(update.expression),
                line=update.line,
                column=update.column,
            )
            for update in stmt.updates
        ]
        return [
            ast.Update(
                record_name=stmt.record_name,
                predicate=_lower_expression(stmt.predicate),
                updates=updates,
                line=stmt.line,
                column=stmt.column,
            )
        ]
    if isinstance(stmt, ast.Delete):
        return [ast.Delete(record_name=stmt.record_name, predicate=_lower_expression(stmt.predicate), line=stmt.line, column=stmt.column)]
    if isinstance(stmt, ast.ThemeChange):
        return [stmt]
    return [stmt]

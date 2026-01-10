from __future__ import annotations

import re
from decimal import Decimal

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
from namel3ss.parser.sugar.lowering.phase3 import (
    _lower_parallel_verb_agents,
    _lower_verb_agent_call,
)
from namel3ss.parser.sugar.lowering.phase4 import _lower_attempt_otherwise


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
    if isinstance(stmt, sugar.AttemptOtherwiseStmt):
        return _lower_attempt_otherwise(stmt, _lower_statements)
    if isinstance(stmt, sugar.RequireLatestStmt):
        return _lower_require_latest(stmt)
    if isinstance(stmt, sugar.ClearStmt):
        return _lower_clear(stmt)
    if isinstance(stmt, sugar.SaveRecordStmt):
        return _lower_save_record(stmt)
    if isinstance(stmt, sugar.NoticeStmt):
        return _lower_notice(stmt)
    if isinstance(stmt, sugar.VerbAgentCallStmt):
        return _lower_verb_agent_call(stmt)
    if isinstance(stmt, sugar.ParallelVerbAgentsStmt):
        return _lower_parallel_verb_agents(stmt)

    if isinstance(stmt, ast.Let):
        if isinstance(stmt.expression, sugar.LatestRecordExpr):
            return _lower_latest_let(stmt, stmt.expression)
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


def _lower_latest_let(stmt: ast.Let, expr: sugar.LatestRecordExpr) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    slug = _record_results_slug(expr.record_name)
    results_name = f"{slug}_results"
    count_name = f"__latest_{slug}_count"
    index_name = f"__latest_{slug}_index"
    find_stmt = ast.Find(
        record_name=expr.record_name,
        predicate=ast.Literal(value=True, line=line, column=column),
        line=line,
        column=column,
    )
    count_stmt = ast.Let(
        name=count_name,
        expression=ast.ListOpExpr(
            kind="length",
            target=ast.VarReference(name=results_name, line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    condition = ast.Comparison(
        kind="gt",
        left=ast.VarReference(name=count_name, line=line, column=column),
        right=ast.Literal(value=Decimal(0), line=line, column=column),
        line=line,
        column=column,
    )
    then_body = [
        ast.Let(
            name=index_name,
            expression=ast.BinaryOp(
                op="-",
                left=ast.VarReference(name=count_name, line=line, column=column),
                right=ast.Literal(value=Decimal(1), line=line, column=column),
                line=line,
                column=column,
            ),
            constant=False,
            line=line,
            column=column,
        ),
        ast.Let(
            name=stmt.name,
            expression=ast.ListOpExpr(
                kind="get",
                target=ast.VarReference(name=results_name, line=line, column=column),
                index=ast.VarReference(name=index_name, line=line, column=column),
                line=line,
                column=column,
            ),
            constant=stmt.constant,
            line=line,
            column=column,
        ),
    ]
    else_body = [
        ast.Let(
            name=stmt.name,
            expression=ast.Literal(value=None, line=line, column=column),
            constant=stmt.constant,
            line=line,
            column=column,
        )
    ]
    return [
        find_stmt,
        count_stmt,
        ast.If(
            condition=condition,
            then_body=then_body,
            else_body=else_body,
            line=line,
            column=column,
        ),
    ]


def _lower_require_latest(stmt: sugar.RequireLatestStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    results_slug = _record_results_slug(stmt.record_name)
    results_name = f"{results_slug}_results"
    count_name = f"__latest_{results_slug}_count"
    index_name = f"__latest_{results_slug}_index"
    missing_value = f"missing_{_record_missing_slug(stmt.record_name)}"
    find_stmt = ast.Find(
        record_name=stmt.record_name,
        predicate=ast.Literal(value=True, line=line, column=column),
        line=line,
        column=column,
    )
    count_stmt = ast.Let(
        name=count_name,
        expression=ast.ListOpExpr(
            kind="length",
            target=ast.VarReference(name=results_name, line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    # The message stays user-controlled text; missing records return a stable sentinel.
    missing_guard = ast.If(
        condition=ast.Comparison(
            kind="eq",
            left=ast.VarReference(name=count_name, line=line, column=column),
            right=ast.Literal(value=Decimal(0), line=line, column=column),
            line=line,
            column=column,
        ),
        then_body=[
            ast.Set(
                target=ast.StatePath(path=["status", "message"], line=line, column=column),
                expression=ast.Literal(value=stmt.message, line=line, column=column),
                line=line,
                column=column,
            ),
            ast.Return(
                expression=ast.Literal(value=missing_value, line=line, column=column),
                line=line,
                column=column,
            )
        ],
        else_body=[],
        line=line,
        column=column,
    )
    index_stmt = ast.Let(
        name=index_name,
        expression=ast.BinaryOp(
            op="-",
            left=ast.VarReference(name=count_name, line=line, column=column),
            right=ast.Literal(value=Decimal(1), line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    target_stmt = ast.Let(
        name=stmt.target,
        expression=ast.ListOpExpr(
            kind="get",
            target=ast.VarReference(name=results_name, line=line, column=column),
            index=ast.VarReference(name=index_name, line=line, column=column),
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )
    return [find_stmt, count_stmt, missing_guard, index_stmt, target_stmt]


_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def _lower_clear(stmt: sugar.ClearStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    return [
        ast.Delete(
            record_name=record_name,
            predicate=ast.Literal(value=True, line=line, column=column),
            line=line,
            column=column,
        )
        for record_name in stmt.record_names
    ]


def _lower_save_record(stmt: sugar.SaveRecordStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    record_slug = _record_missing_slug(stmt.record_name)
    temp_name = f"__save_{record_slug}_payload"
    binding_name = record_slug
    statements: list[ast.Statement] = []
    for field in stmt.fields:
        statements.append(
            ast.Set(
                target=ast.StatePath(path=[temp_name] + field.path, line=field.line, column=field.column),
                expression=_lower_expression(field.expression),
                line=field.line,
                column=field.column,
            )
        )
    statements.append(
        ast.Create(
            record_name=stmt.record_name,
            values=ast.StatePath(path=[temp_name], line=line, column=column),
            target=binding_name,
            line=line,
            column=column,
        )
    )
    return statements


def _lower_notice(stmt: sugar.NoticeStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    return [
        ast.Set(
            target=ast.StatePath(path=["notice"], line=line, column=column),
            expression=ast.Literal(value=stmt.message, line=line, column=column),
            line=line,
            column=column,
        )
    ]


def _record_results_slug(record_name: str) -> str:
    parts = [part.lower() for part in record_name.split(".") if part]
    return "_".join(parts) if parts else "record"


def _record_missing_slug(record_name: str) -> str:
    parts = [part for part in record_name.split(".") if part]
    if not parts:
        return "record"
    normalized = [_CAMEL_BOUNDARY.sub(r"\1_\2", part).lower() for part in parts]
    return "_".join(normalized)

from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar import grammar as sugar
from namel3ss.parser.sugar.lowering.builders import (
    _and_predicate,
    _delete_by_run_id,
    _delete_metric,
    _eq,
    _metric_meta,
    _number,
    _set_state,
    _set_state_block,
    _state_expr,
    _timeline_event,
    _var,
    _write_metric,
)
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


def _lower_start_run(stmt: sugar.StartRunStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    statements: list[ast.Statement] = [
        _set_state(["run_id"], ast.Literal(value="current", line=line, column=column), line, column),
        _set_state(["ai_calls"], _number(0, line, column), line, column),
        _set_state(["tool_calls"], _number(0, line, column), line, column),
        _set_state(["policy_violations"], _number(0, line, column), line, column),
        _set_state(["blocked_reason"], ast.Literal(value="not run", line=line, column=column), line, column),
    ]
    statements.extend(_delete_by_run_id("TimelineEvent", line, column))
    statements.extend(_delete_by_run_id("AgentOutput", line, column))
    statements.extend(_delete_by_run_id("RunResult", line, column))
    statements.extend(_delete_by_run_id("ExplainNote", line, column))
    statements.extend(_delete_by_run_id("SafetyStatus", line, column))
    statements.extend(_delete_by_run_id("DebugMetric", line, column))
    start_detail = _lower_expression(stmt.goal) if stmt.goal else ast.Literal(value="run started", line=line, column=column)
    statements.extend(_timeline_event(seq=1, stage="Start", detail=start_detail, line=line, column=column))
    memory_detail = ast.Literal(value=f"pack: {stmt.memory_pack}", line=line, column=column)
    statements.extend(_timeline_event(seq=2, stage="Memory", detail=memory_detail, line=line, column=column))
    return statements


def _lower_plan(stmt: sugar.PlanWithAgentStmt) -> ast.Statement:
    input_expr = _lower_expression(stmt.input_expr) if stmt.input_expr else ast.VarReference(name="goal", line=stmt.line, column=stmt.column)
    return ast.RunAgentStmt(
        agent_name=stmt.agent_name,
        input_expr=input_expr,
        target="plan",
        line=stmt.line,
        column=stmt.column,
    )


def _lower_review(stmt: sugar.ReviewParallelStmt) -> ast.Statement:
    entries = [
        ast.ParallelAgentEntry(
            agent_name=name,
            input_expr=ast.VarReference(name="plan", line=stmt.line, column=stmt.column),
            line=stmt.line,
            column=stmt.column,
        )
        for name in stmt.agent_names
    ]
    merge = ast.AgentMergePolicy(
        policy="all",
        require_keys=None,
        require_non_empty=None,
        score_key=None,
        score_rule=None,
        min_consensus=None,
        consensus_key=None,
        line=stmt.line,
        column=stmt.column,
    )
    return ast.RunAgentsParallelStmt(
        entries=entries,
        target=stmt.target,
        merge=merge,
        line=stmt.line,
        column=stmt.column,
    )


def _lower_timeline(stmt: sugar.TimelineShowStmt) -> list[ast.Statement]:
    statements: list[ast.Statement] = []
    for idx, entry in enumerate(stmt.entries, start=1):
        detail = _lower_expression(entry.detail) if entry.detail is not None else ast.Literal(value=None, line=entry.line, column=entry.column)
        statements.extend(_timeline_event(seq=idx, stage=entry.stage, detail=detail, line=entry.line, column=entry.column))
    return statements


def _lower_compute_hash(stmt: sugar.ComputeOutputHashStmt) -> ast.Statement:
    line = stmt.line
    column = stmt.column
    return ast.Let(
        name="hash_result",
        expression=ast.ToolCallExpr(
            tool_name="hash text",
            arguments=[
                ast.ToolCallArg(
                    name="value",
                    value=ast.VarReference(name="final_output", line=line, column=column),
                    line=line,
                    column=column,
                )
            ],
            line=line,
            column=column,
        ),
        constant=False,
        line=line,
        column=column,
    )


def _lower_record_output(stmt: sugar.RecordFinalOutputStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    statements: list[ast.Statement] = []
    statements.extend(
        _set_state_block(
            ["result_record"],
            {
                "run_id": _state_expr(["run_id"], line, column),
                "mode": ast.VarReference(name="mode", line=line, column=column),
                "output": ast.VarReference(name="final_output", line=line, column=column),
                "output_hash": ast.AttrAccess(base="hash_result", attrs=["hash"], line=line, column=column),
                "merge_policy": ast.VarReference(name="merge_policy", line=line, column=column),
                "status": ast.Literal(value="ok", line=line, column=column),
            },
            line,
            column,
        )
    )
    statements.append(
        ast.Create(
            record_name="RunResult",
            values=_state_expr(["result_record"], line, column),
            target="result",
            line=line,
            column=column,
        )
    )
    return statements


def _lower_increment_metric(stmt: sugar.IncrementMetricStmt) -> list[ast.Statement]:
    metric = stmt.metric
    line = stmt.line
    column = stmt.column
    seq, label = _metric_meta(metric)
    statements = [
        _set_state(
            [metric],
            ast.BinaryOp(
                op="+",
                left=_state_expr([metric], line, column),
                right=_number(1, line, column),
                line=line,
                column=column,
            ),
            line,
            column,
        )
    ]
    statements.extend(_delete_metric(label, line, column))
    statements.extend(_write_metric(label, seq, metric, line, column))
    return statements


def _lower_policy_violation(stmt: sugar.RecordPolicyViolationStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    metric = "policy_violations"
    seq, label = _metric_meta(metric)
    statements = [
        _set_state(
            [metric],
            ast.BinaryOp(
                op="+",
                left=_state_expr([metric], line, column),
                right=_number(1, line, column),
                line=line,
                column=column,
            ),
            line,
            column,
        )
    ]
    statements.extend(_delete_metric(label, line, column))
    statements.extend(_write_metric(label, seq, metric, line, column))
    return statements


def _lower_attempt_blocked(stmt: sugar.AttemptBlockedToolStmt) -> list[ast.Statement]:
    line = stmt.line
    column = stmt.column
    try_body = [
        ast.Let(
            name="blocked",
            expression=ast.ToolCallExpr(
                tool_name=stmt.tool_name,
                arguments=[
                    ast.ToolCallArg(
                        name="url",
                        value=_lower_expression(stmt.argument),
                        line=line,
                        column=column,
                    )
                ],
                line=line,
                column=column,
            ),
            constant=False,
            line=line,
            column=column,
        ),
        _set_state(
            ["blocked_reason"],
            ast.Literal(value="unexpected success", line=line, column=column),
            line,
            column,
        ),
    ]
    catch_body = [
        _set_state(
            ["blocked_reason"],
            ast.Literal(value="blocked by policy (see Traces)", line=line, column=column),
            line,
            column,
        ),
        _set_state(
            ["policy_violations"],
            ast.BinaryOp(
                op="+",
                left=_state_expr(["policy_violations"], line, column),
                right=_number(1, line, column),
                line=line,
                column=column,
            ),
            line,
            column,
        ),
    ]
    statements: list[ast.Statement] = [
        ast.TryCatch(try_body=try_body, catch_var="err", catch_body=catch_body, line=line, column=column)
    ]
    statements.append(
        _set_state(
            ["tool_calls"],
            ast.BinaryOp(
                op="+",
                left=_state_expr(["tool_calls"], line, column),
                right=_number(1, line, column),
                line=line,
                column=column,
            ),
            line,
            column,
        )
    )
    statements.extend(_delete_by_run_id("SafetyStatus", line, column))
    statements.extend(
        _set_state_block(
            ["safety_status"],
            {
                "run_id": _state_expr(["run_id"], line, column),
                "blocked_reason": _state_expr(["blocked_reason"], line, column),
                "confirmation_status": ast.Literal(value="not confirmed", line=line, column=column),
            },
            line,
            column,
        )
    )
    statements.append(
        ast.Create(
            record_name="SafetyStatus",
            values=_state_expr(["safety_status"], line, column),
            target="status",
            line=line,
            column=column,
        )
    )
    statements.append(
        ast.Delete(
            record_name="TimelineEvent",
            predicate=_and_predicate(
                _eq(_var("run_id", line, column), _state_expr(["run_id"], line, column), line, column),
                _eq(_var("stage", line, column), ast.Literal(value="Safety", line=line, column=column), line, column),
                line,
                column,
            ),
            line=line,
            column=column,
        )
    )
    statements.extend(
        _timeline_event(
            seq=8,
            stage="Safety",
            detail=_state_expr(["blocked_reason"], line, column),
            line=line,
            column=column,
        )
    )
    statements.extend(_delete_metric("Tool calls", line, column))
    statements.extend(_delete_metric("Policy violations", line, column))
    statements.extend(_write_metric("Tool calls", 2, "tool_calls", line, column))
    statements.extend(_write_metric("Policy violations", 3, "policy_violations", line, column))
    return statements

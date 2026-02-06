from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.pipelines.registry import pipeline_purity
from namel3ss.purity import is_pure, pure_effect_message


EFFECTFUL_BUILTINS = {"secret", "auth_bearer", "auth_basic", "auth_header"}


def validate_flow_purity(flows: list[ir.Flow], flow_contracts: dict[str, ir.ContractDecl]) -> None:
    flow_map = {flow.name: flow for flow in flows}
    for flow in flows:
        if not is_pure(getattr(flow, "purity", None)):
            continue
        if flow.name not in flow_contracts:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Pure flow "{flow.name}" is missing a contract.',
                    why="Pure flows require explicit input and output contracts.",
                    fix="Add a contract flow block for the pure flow.",
                    example=(
                        f'contract flow "{flow.name}":\n  input:\n    value is text\n  output:\n    result is text'
                    ),
                ),
                line=flow.line,
                column=flow.column,
            )
        if getattr(flow, "declarative", False):
            _validate_pure_declarative_flow(flow)
        _scan_statements(flow, flow_map, flow.body)


def _validate_pure_declarative_flow(flow: ir.Flow) -> None:
    steps = getattr(flow, "steps", None) or []
    for step in steps:
        if isinstance(step, ir.FlowCreate):
            _raise_effect(flow, "create records", line=step.line, column=step.column)
        if isinstance(step, ir.FlowUpdate):
            _raise_effect(flow, "update records", line=step.line, column=step.column)
        if isinstance(step, ir.FlowDelete):
            _raise_effect(flow, "delete records", line=step.line, column=step.column)
        if isinstance(step, ir.FlowCallForeign):
            _raise_effect(flow, f'call foreign "{step.foreign_name}"', line=step.line, column=step.column)


def _scan_statements(flow: ir.Flow, flow_map: dict[str, ir.Flow], stmts: list[ir.Statement]) -> None:
    for stmt in stmts:
        _scan_statement(flow, flow_map, stmt)


def _scan_statement(flow: ir.Flow, flow_map: dict[str, ir.Flow], stmt: ir.Statement) -> None:
    if isinstance(stmt, ir.Let):
        _scan_expression(flow, flow_map, stmt.expression)
        return
    if isinstance(stmt, ir.Set):
        if isinstance(stmt.target, ir.StatePath):
            _raise_effect(flow, "write state", line=stmt.line, column=stmt.column)
        _scan_expression(flow, flow_map, stmt.expression)
        return
    if isinstance(stmt, ir.If):
        _scan_expression(flow, flow_map, stmt.condition)
        _scan_statements(flow, flow_map, stmt.then_body)
        _scan_statements(flow, flow_map, stmt.else_body)
        return
    if isinstance(stmt, ir.Return):
        _scan_expression(flow, flow_map, stmt.expression)
        return
    if isinstance(stmt, ir.AwaitStmt):
        return
    if isinstance(stmt, ir.YieldStmt):
        _scan_expression(flow, flow_map, stmt.expression)
        return
    if isinstance(stmt, ir.Repeat):
        _scan_expression(flow, flow_map, stmt.count)
        _scan_statements(flow, flow_map, stmt.body)
        return
    if isinstance(stmt, ir.RepeatWhile):
        _scan_expression(flow, flow_map, stmt.condition)
        _scan_statements(flow, flow_map, stmt.body)
        return
    if isinstance(stmt, ir.ForEach):
        _scan_expression(flow, flow_map, stmt.iterable)
        _scan_statements(flow, flow_map, stmt.body)
        return
    if isinstance(stmt, ir.Match):
        _scan_expression(flow, flow_map, stmt.expression)
        for case in stmt.cases:
            _scan_expression(flow, flow_map, case.pattern)
            _scan_statements(flow, flow_map, case.body)
        if stmt.otherwise is not None:
            _scan_statements(flow, flow_map, stmt.otherwise)
        return
    if isinstance(stmt, ir.TryCatch):
        _scan_statements(flow, flow_map, stmt.try_body)
        _scan_statements(flow, flow_map, stmt.catch_body)
        return
    if isinstance(stmt, ir.ParallelBlock):
        for task in stmt.tasks:
            _scan_statements(flow, flow_map, task.body)
        return
    if isinstance(stmt, ir.OrchestrationBlock):
        for branch in stmt.branches:
            _scan_expression(flow, flow_map, branch.call_expr)
        return
    if isinstance(stmt, ir.AskAIStmt):
        _raise_effect(flow, f'call ai "{stmt.ai_name}"', line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.RunAgentStmt):
        _raise_effect(flow, f'run agent "{stmt.agent_name}"', line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.RunAgentsParallelStmt):
        _raise_effect(flow, "run agents in parallel", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.Save):
        _raise_effect(flow, "save records", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.Create):
        _raise_effect(flow, "create records", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.Update):
        _raise_effect(flow, "update records", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.Delete):
        _raise_effect(flow, "delete records", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.Find):
        _scan_expression(flow, flow_map, stmt.predicate)
        return
    if isinstance(stmt, ir.LogStmt):
        _scan_expression(flow, flow_map, stmt.message)
        if stmt.fields is not None:
            _scan_expression(flow, flow_map, stmt.fields)
        return
    if isinstance(stmt, ir.MetricStmt):
        if stmt.value is not None:
            _scan_expression(flow, flow_map, stmt.value)
        if stmt.labels is not None:
            _scan_expression(flow, flow_map, stmt.labels)
        return
    if isinstance(stmt, ir.EnqueueJob):
        _raise_effect(flow, f'enqueue job "{stmt.job_name}"', line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.AdvanceTime):
        _raise_effect(flow, "advance time", line=stmt.line, column=stmt.column)
    if isinstance(stmt, ir.ThemeChange):
        return


def _scan_expression(flow: ir.Flow, flow_map: dict[str, ir.Flow], expr: ir.Expression) -> None:
    if isinstance(expr, ir.AsyncCallExpr):
        _scan_expression(flow, flow_map, expr.expression)
        return
    if isinstance(expr, ir.CallFlowExpr):
        callee = flow_map.get(expr.flow_name)
        if callee and not is_pure(getattr(callee, "purity", None)):
            _raise_effect(flow, f'call effectful flow "{expr.flow_name}"', line=expr.line, column=expr.column)
        for arg in expr.arguments:
            _scan_expression(flow, flow_map, arg.value)
        return
    if isinstance(expr, ir.CallPipelineExpr):
        if not is_pure(pipeline_purity(expr.pipeline_name)):
            _raise_effect(
                flow,
                f'call effectful pipeline "{expr.pipeline_name}"',
                line=expr.line,
                column=expr.column,
            )
        for arg in expr.arguments:
            _scan_expression(flow, flow_map, arg.value)
        return
    if isinstance(expr, ir.ToolCallExpr):
        _raise_effect(flow, f'call tool "{expr.tool_name}"', line=expr.line, column=expr.column)
    if isinstance(expr, ir.BuiltinCallExpr):
        if expr.name in EFFECTFUL_BUILTINS:
            _raise_effect(flow, f'call {expr.name}', line=expr.line, column=expr.column)
        for arg in expr.arguments:
            _scan_expression(flow, flow_map, arg)
        return
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            _scan_expression(flow, flow_map, arg.value)
        return
    if isinstance(expr, ir.UnaryOp):
        _scan_expression(flow, flow_map, expr.operand)
        return
    if isinstance(expr, ir.BinaryOp):
        _scan_expression(flow, flow_map, expr.left)
        _scan_expression(flow, flow_map, expr.right)
        return
    if isinstance(expr, ir.Comparison):
        _scan_expression(flow, flow_map, expr.left)
        _scan_expression(flow, flow_map, expr.right)
        return
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            _scan_expression(flow, flow_map, item)
        return
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            _scan_expression(flow, flow_map, entry.key)
            _scan_expression(flow, flow_map, entry.value)
        return
    if isinstance(expr, ir.ListOpExpr):
        _scan_expression(flow, flow_map, expr.target)
        if expr.value is not None:
            _scan_expression(flow, flow_map, expr.value)
        if expr.index is not None:
            _scan_expression(flow, flow_map, expr.index)
        return
    if isinstance(expr, ir.ListMapExpr):
        _scan_expression(flow, flow_map, expr.target)
        _scan_expression(flow, flow_map, expr.body)
        return
    if isinstance(expr, ir.ListFilterExpr):
        _scan_expression(flow, flow_map, expr.target)
        _scan_expression(flow, flow_map, expr.predicate)
        return
    if isinstance(expr, ir.ListReduceExpr):
        _scan_expression(flow, flow_map, expr.target)
        _scan_expression(flow, flow_map, expr.start)
        _scan_expression(flow, flow_map, expr.body)
        return
    if isinstance(expr, ir.MapOpExpr):
        _scan_expression(flow, flow_map, expr.target)
        if expr.key is not None:
            _scan_expression(flow, flow_map, expr.key)
        if expr.value is not None:
            _scan_expression(flow, flow_map, expr.value)
        return


def _raise_effect(flow: ir.Flow, effect: str, *, line: int | None, column: int | None) -> None:
    raise Namel3ssError(
        pure_effect_message(effect, flow_name=flow.name),
        line=line if line is not None else flow.line,
        column=column if column is not None else flow.column,
    )


__all__ = ["validate_flow_purity"]

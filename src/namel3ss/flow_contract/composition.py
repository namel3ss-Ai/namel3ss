from __future__ import annotations

import difflib

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir

FlowCallEdge = tuple[str, int | None, int | None]


def validate_flow_contracts(
    flows: list[ir.Flow],
    flow_contracts: dict[str, ir.ContractDecl],
) -> None:
    flow_names = {flow.name for flow in flows}
    for name, contract in flow_contracts.items():
        if name in flow_names:
            continue
        raise Namel3ssError(
            build_guidance_message(
                what=f'Contract references unknown flow "{name}".',
                why="Contracts must refer to flows declared in the app.",
                fix="Add the missing flow or update the contract name.",
                example=f'flow "{name}":\\n  return "ok"',
            ),
            line=contract.line,
            column=contract.column,
        )


def validate_flow_composition(
    flows: list[ir.Flow],
    flow_contracts: dict[str, ir.ContractDecl],
    pipeline_contracts: dict[str, ir.ContractDecl],
) -> None:
    flow_names = [flow.name for flow in flows]
    flow_map = {flow.name: flow for flow in flows}
    call_graph: dict[str, list[FlowCallEdge]] = {flow.name: [] for flow in flows}

    for flow in flows:
        flow_calls: list[ir.CallFlowExpr] = []
        pipeline_calls: list[ir.CallPipelineExpr] = []
        _collect_calls(flow.body, flow_calls, pipeline_calls)
        for call in flow_calls:
            _validate_flow_call(call, flow_contracts, flow_map, flow_names)
            call_graph[flow.name].append((call.flow_name, call.line, call.column))
        for call in pipeline_calls:
            _validate_pipeline_call(call, pipeline_contracts)

    _validate_call_graph(call_graph, flows)


def _validate_flow_call(
    call: ir.CallFlowExpr,
    flow_contracts: dict[str, ir.ContractDecl],
    flow_map: dict[str, ir.Flow],
    flow_names: list[str],
) -> None:
    flow_name = call.flow_name
    flow = flow_map.get(flow_name)
    if flow is None:
        suggestion = _suggest_flow_name(flow_name, flow_names)
        hint = f' Did you mean "{suggestion}"?' if suggestion else ""
        raise Namel3ssError(
            build_guidance_message(
                what=f'Unknown flow "{flow_name}".{hint}',
                why="Flow calls must reference declared flows.",
                fix="Update the call to an existing flow.",
                example=f'flow "{flow_name}":\\n  return "ok"',
            ),
            line=call.line,
            column=call.column,
        )
    contract = flow_contracts.get(flow_name)
    if contract is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Flow "{flow_name}" is missing a contract.',
                why="Composed flows require explicit input and output contracts.",
                fix="Add a contract flow block for the called flow.",
                example=f'contract flow "{flow_name}":\\n  input:\\n    value is text\\n  output:\\n    result is text',
            ),
            line=call.line,
            column=call.column,
        )
    signature = contract.signature
    _validate_call_fields(
        call_names=[arg.name for arg in call.arguments],
        contract_fields=signature.inputs,
        label="input",
        kind="flow",
        line=call.line,
        column=call.column,
    )
    _validate_call_fields(
        call_names=list(call.outputs),
        contract_fields=signature.outputs or [],
        label="output",
        kind="flow",
        line=call.line,
        column=call.column,
    )


def _validate_pipeline_call(call: ir.CallPipelineExpr, pipeline_contracts: dict[str, ir.ContractDecl]) -> None:
    pipeline = pipeline_contracts.get(call.pipeline_name)
    if pipeline is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Unknown pipeline "{call.pipeline_name}".',
                why="Pipeline calls must reference a known pipeline.",
                fix="Use a supported pipeline name.",
                example='call pipeline "retrieval":\\n  input:\\n    query is "invoice"\\n  output:\\n    report',
            ),
            line=call.line,
            column=call.column,
        )
    signature = pipeline.signature
    _validate_call_fields(
        call_names=[arg.name for arg in call.arguments],
        contract_fields=signature.inputs,
        label="input",
        kind="pipeline",
        line=call.line,
        column=call.column,
    )
    _validate_call_fields(
        call_names=list(call.outputs),
        contract_fields=signature.outputs or [],
        label="output",
        kind="pipeline",
        line=call.line,
        column=call.column,
    )


def _validate_call_fields(
    *,
    call_names: list[str],
    contract_fields: list[ir.FunctionParam],
    label: str,
    kind: str,
    line: int | None,
    column: int | None,
) -> None:
    if not contract_fields and call_names:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{kind.title()} call lists {label}s that are not declared.",
                why=f"The {kind} contract declares no {label}s.",
                fix=f"Remove the extra {label} entries.",
                example=f"{label}:",
            ),
            line=line,
            column=column,
        )
    if contract_fields and not call_names:
        raise Namel3ssError(
            build_guidance_message(
                what=f"{kind.title()} call is missing {label}s.",
                why=f"The {kind} contract requires explicit {label}s.",
                fix=f"Declare the {label} block with the required fields.",
                example=f"{label}:",
            ),
            line=line,
            column=column,
        )
    order = {field.name: idx for idx, field in enumerate(contract_fields)}
    indices: list[int] = []
    for name in call_names:
        if name not in order:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Unknown {label} "{name}".',
                    why=f"The {kind} contract does not declare this {label}.",
                    fix=f"Use the declared {label} names in order.",
                    example=f"{label}:\\n  {contract_fields[0].name}" if contract_fields else f"{label}:",
                ),
                line=line,
                column=column,
            )
        indices.append(order[name])
    if indices != sorted(indices):
        ordered = ", ".join(field.name for field in contract_fields)
        raise Namel3ssError(
            build_guidance_message(
                what=f"{kind.title()} {label}s are out of order.",
                why="Inputs and outputs must follow the contract order.",
                fix=f"Reorder the {label} block to match the contract.",
                example=f"{label}:\\n  {ordered}" if ordered else f"{label}:",
            ),
            line=line,
            column=column,
        )
    missing = [field.name for field in contract_fields if field.required and field.name not in call_names]
    if missing:
        missing_text = ", ".join(missing)
        raise Namel3ssError(
            build_guidance_message(
                what=f"Missing required {label}s: {missing_text}.",
                why=f"All required {label}s must be provided.",
                fix=f"Add the missing {label}s in order.",
                example=f"{label}:\\n  {missing[0]}",
            ),
            line=line,
            column=column,
        )


def _collect_calls(
    stmts: list[ir.Statement],
    flow_calls: list[ir.CallFlowExpr],
    pipeline_calls: list[ir.CallPipelineExpr],
) -> None:
    for stmt in stmts:
        if isinstance(stmt, ir.Let):
            _collect_calls_from_expr(stmt.expression, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Set):
            _collect_calls_from_expr(stmt.expression, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Return):
            _collect_calls_from_expr(stmt.expression, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.If):
            _collect_calls_from_expr(stmt.condition, flow_calls, pipeline_calls)
            _collect_calls(stmt.then_body, flow_calls, pipeline_calls)
            _collect_calls(stmt.else_body, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Repeat):
            _collect_calls_from_expr(stmt.count, flow_calls, pipeline_calls)
            _collect_calls(stmt.body, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.RepeatWhile):
            _collect_calls_from_expr(stmt.condition, flow_calls, pipeline_calls)
            _collect_calls(stmt.body, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.ForEach):
            _collect_calls_from_expr(stmt.iterable, flow_calls, pipeline_calls)
            _collect_calls(stmt.body, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Match):
            _collect_calls_from_expr(stmt.expression, flow_calls, pipeline_calls)
            for case in stmt.cases:
                _collect_calls_from_expr(case.pattern, flow_calls, pipeline_calls)
                _collect_calls(case.body, flow_calls, pipeline_calls)
            if stmt.otherwise is not None:
                _collect_calls(stmt.otherwise, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.TryCatch):
            _collect_calls(stmt.try_body, flow_calls, pipeline_calls)
            _collect_calls(stmt.catch_body, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.ParallelBlock):
            for task in stmt.tasks:
                _collect_calls(task.body, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.LogStmt):
            _collect_calls_from_expr(stmt.message, flow_calls, pipeline_calls)
            if stmt.fields is not None:
                _collect_calls_from_expr(stmt.fields, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.MetricStmt):
            if stmt.value is not None:
                _collect_calls_from_expr(stmt.value, flow_calls, pipeline_calls)
            if stmt.labels is not None:
                _collect_calls_from_expr(stmt.labels, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Create):
            _collect_calls_from_expr(stmt.values, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Update):
            _collect_calls_from_expr(stmt.predicate, flow_calls, pipeline_calls)
            for update in stmt.updates:
                _collect_calls_from_expr(update.expression, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Delete):
            _collect_calls_from_expr(stmt.predicate, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.Find):
            _collect_calls_from_expr(stmt.predicate, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.EnqueueJob):
            if stmt.input_expr is not None:
                _collect_calls_from_expr(stmt.input_expr, flow_calls, pipeline_calls)
            if stmt.schedule_expr is not None:
                _collect_calls_from_expr(stmt.schedule_expr, flow_calls, pipeline_calls)
        elif isinstance(stmt, ir.AdvanceTime):
            _collect_calls_from_expr(stmt.amount, flow_calls, pipeline_calls)


def _collect_calls_from_expr(
    expr: ir.Expression,
    flow_calls: list[ir.CallFlowExpr],
    pipeline_calls: list[ir.CallPipelineExpr],
) -> None:
    if isinstance(expr, ir.CallFlowExpr):
        flow_calls.append(expr)
        for arg in expr.arguments:
            _collect_calls_from_expr(arg.value, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.CallPipelineExpr):
        pipeline_calls.append(expr)
        for arg in expr.arguments:
            _collect_calls_from_expr(arg.value, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.CallFunctionExpr):
        for arg in expr.arguments:
            _collect_calls_from_expr(arg.value, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.ToolCallExpr):
        for arg in expr.arguments:
            _collect_calls_from_expr(arg.value, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.UnaryOp):
        _collect_calls_from_expr(expr.operand, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.BinaryOp):
        _collect_calls_from_expr(expr.left, flow_calls, pipeline_calls)
        _collect_calls_from_expr(expr.right, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.Comparison):
        _collect_calls_from_expr(expr.left, flow_calls, pipeline_calls)
        _collect_calls_from_expr(expr.right, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.ListExpr):
        for item in expr.items:
            _collect_calls_from_expr(item, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.MapExpr):
        for entry in expr.entries:
            _collect_calls_from_expr(entry.key, flow_calls, pipeline_calls)
            _collect_calls_from_expr(entry.value, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.ListOpExpr):
        _collect_calls_from_expr(expr.target, flow_calls, pipeline_calls)
        if expr.value is not None:
            _collect_calls_from_expr(expr.value, flow_calls, pipeline_calls)
        if expr.index is not None:
            _collect_calls_from_expr(expr.index, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.ListMapExpr):
        _collect_calls_from_expr(expr.target, flow_calls, pipeline_calls)
        _collect_calls_from_expr(expr.body, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.ListFilterExpr):
        _collect_calls_from_expr(expr.target, flow_calls, pipeline_calls)
        _collect_calls_from_expr(expr.predicate, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.ListReduceExpr):
        _collect_calls_from_expr(expr.target, flow_calls, pipeline_calls)
        _collect_calls_from_expr(expr.start, flow_calls, pipeline_calls)
        _collect_calls_from_expr(expr.body, flow_calls, pipeline_calls)
        return
    if isinstance(expr, ir.MapOpExpr):
        _collect_calls_from_expr(expr.target, flow_calls, pipeline_calls)
        if expr.key is not None:
            _collect_calls_from_expr(expr.key, flow_calls, pipeline_calls)
        if expr.value is not None:
            _collect_calls_from_expr(expr.value, flow_calls, pipeline_calls)
        return


def _validate_call_graph(call_graph: dict[str, list[FlowCallEdge]], flows: list[ir.Flow]) -> None:
    flow_order = [flow.name for flow in flows]
    flow_lookup = {flow.name: flow for flow in flows}
    visiting: list[str] = []
    visiting_set: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        visiting.append(name)
        visiting_set.add(name)
        for target, line, column in call_graph.get(name, []):
            if target not in flow_lookup:
                continue
            if target in visiting_set:
                cycle = _format_cycle(_cycle_path(visiting, target))
                error_line = line if line is not None else flow_lookup[name].line
                error_column = column if column is not None else flow_lookup[name].column
                raise Namel3ssError(
                    f"Flow call cycle detected: {cycle}",
                    line=error_line,
                    column=error_column,
                )
            if target not in visited:
                visit(target)
        visiting_set.remove(name)
        visiting.pop()
        visited.add(name)

    for name in flow_order:
        if name not in visited:
            visit(name)


def _cycle_path(stack: list[str], target: str) -> list[str]:
    if target not in stack:
        return [target, target]
    start = stack.index(target)
    return stack[start:] + [target]


def _format_cycle(path: list[str]) -> str:
    return " -> ".join(path)


def _suggest_flow_name(name: str, flow_names: list[str]) -> str | None:
    if not flow_names:
        return None
    matches = difflib.get_close_matches(name, flow_names, n=1, cutoff=0.6)
    return matches[0] if matches else None


__all__ = ["validate_flow_composition", "validate_flow_contracts"]

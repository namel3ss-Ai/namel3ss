from __future__ import annotations

import copy
import difflib

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.audit.recorder import record_audit_entry
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.execution.recorder import record_step
from namel3ss.runtime.values.coerce import require_type
from namel3ss.secrets import collect_secret_values
from namel3ss.traces.schema import TraceEventType


def execute_flow_call(
    ctx: ExecutionContext,
    expr: ir.CallFlowExpr,
    evaluate_expression,
    collector=None,
) -> object:
    if getattr(ctx, "call_stack", []):
        raise Namel3ssError("Functions cannot call flows", line=expr.line, column=expr.column)
    flow = _lookup_flow(ctx, expr.flow_name, line=expr.line, column=expr.column)
    contract = _lookup_flow_contract(ctx, expr.flow_name, line=expr.line, column=expr.column)
    args_by_name = _evaluate_call_args(ctx, expr.arguments, evaluate_expression, collector)
    input_payload = _build_input_payload(contract.signature, args_by_name, expr)
    contract_inputs = [param.name for param in contract.signature.inputs]
    contract_outputs = [param.name for param in contract.signature.outputs or []]
    flow_call_id = _next_flow_call_id(ctx)
    caller_flow = getattr(getattr(ctx, "flow", None), "name", None)

    _record_flow_call_started(
        ctx,
        flow_call_id,
        caller_flow,
        flow.name,
        expr,
        contract_inputs,
        contract_outputs,
    )
    record_step(
        ctx,
        kind="flow_call_start",
        what=f'call flow "{flow.name}"',
        data={
            "flow_call_id": flow_call_id,
            "callee_flow": flow.name,
            "contract_inputs": contract_inputs,
            "contract_outputs": contract_outputs,
        },
        line=expr.line,
        column=expr.column,
    )

    audit_before = None
    record_start = 0
    if getattr(flow, "audited", False):
        audit_before = copy.deepcopy(ctx.state)
        record_start = len(getattr(ctx, "record_changes", []))

    try:
        result_value = _run_flow(ctx, flow, input_payload, flow_call_id)
        output_map = _validate_flow_output(contract.signature, result_value, expr)
        selected = _select_outputs(output_map, expr.outputs, expr)
    except Exception as exc:
        _record_flow_call_finished(
            ctx,
            flow_call_id,
            caller_flow,
            flow.name,
            status="error",
            error=exc,
            contract_inputs=contract_inputs,
            contract_outputs=contract_outputs,
        )
        record_step(
            ctx,
            kind="flow_call_error",
            what=f'call flow "{flow.name}" failed',
            because=str(exc),
            data={
                "flow_call_id": flow_call_id,
                "callee_flow": flow.name,
                "contract_inputs": contract_inputs,
                "contract_outputs": contract_outputs,
            },
            line=expr.line,
            column=expr.column,
        )
        raise

    if audit_before is not None:
        record_changes = list(getattr(ctx, "record_changes", []))
        record_slice = record_changes[record_start:]
        record_audit_entry(
            ctx.store,
            flow_name=flow.name,
            action_name=getattr(ctx, "flow_action_id", None),
            identity=ctx.identity,
            before=audit_before,
            after=ctx.state,
            record_changes=record_slice,
            project_root=ctx.project_root,
            secret_values=collect_secret_values(ctx.config),
        )

    _record_flow_call_finished(
        ctx,
        flow_call_id,
        caller_flow,
        flow.name,
        status="ok",
        error=None,
        contract_inputs=contract_inputs,
        contract_outputs=contract_outputs,
    )
    record_step(
        ctx,
        kind="flow_call_end",
        what=f'call flow "{flow.name}" finished',
        data={
            "flow_call_id": flow_call_id,
            "callee_flow": flow.name,
            "contract_inputs": contract_inputs,
            "contract_outputs": contract_outputs,
        },
        line=expr.line,
        column=expr.column,
    )
    return selected


def _run_flow(ctx: ExecutionContext, flow: ir.Flow, input_payload: dict, flow_call_id: str) -> object:
    if flow.name in getattr(ctx, "flow_stack", []):
        raise Namel3ssError("Flow recursion is not allowed", line=flow.line, column=flow.column)
    from namel3ss.runtime.executor.signals import _ReturnSignal
    from namel3ss.runtime.executor.statements import execute_statement
    from namel3ss.runtime.identity.guards import enforce_requires
    from namel3ss.runtime.mutation_policy import requires_mentions_mutation

    parent_flow = ctx.flow
    parent_locals = ctx.locals
    parent_constants = ctx.constants
    parent_last_value = ctx.last_value
    parent_statement = getattr(ctx, "current_statement", None)
    parent_statement_index = getattr(ctx, "current_statement_index", None)
    parent_flow_call_id = getattr(ctx, "flow_call_id", None)

    call_locals = {"input": input_payload}
    if isinstance(parent_locals, dict) and "secrets" in parent_locals:
        call_locals["secrets"] = parent_locals["secrets"]

    ctx.flow = flow
    ctx.locals = call_locals
    ctx.constants = set()
    ctx.last_value = None
    ctx.current_statement = None
    ctx.current_statement_index = None
    ctx.flow_call_id = flow_call_id
    ctx.flow_stack.append(flow.name)

    result_value = None
    try:
        requires_expr = getattr(flow, "requires", None)
        if not requires_mentions_mutation(requires_expr):
            enforce_requires(
                ctx,
                requires_expr,
                subject=f'flow "{flow.name}"',
                line=flow.line,
                column=flow.column,
            )
        if getattr(flow, "declarative", False):
            from namel3ss.runtime.flow.runner import run_declarative_flow

            run_declarative_flow(ctx)
        else:
            for idx, stmt in enumerate(flow.body, start=1):
                ctx.current_statement = stmt
                ctx.current_statement_index = idx
                execute_statement(ctx, stmt)
    except _ReturnSignal as signal:
        ctx.last_value = signal.value
    finally:
        result_value = ctx.last_value
        ctx.flow_stack.pop()
        ctx.flow = parent_flow
        ctx.locals = parent_locals
        ctx.constants = parent_constants
        ctx.last_value = parent_last_value
        ctx.current_statement = parent_statement
        ctx.current_statement_index = parent_statement_index
        ctx.flow_call_id = parent_flow_call_id

    return result_value


def _evaluate_call_args(ctx: ExecutionContext, arguments: list[ir.CallArg], evaluate_expression, collector=None) -> dict[str, object]:
    args_by_name: dict[str, object] = {}
    for arg in arguments:
        if arg.name in args_by_name:
            raise Namel3ssError(
                f"Duplicate flow input '{arg.name}'",
                line=arg.line,
                column=arg.column,
            )
        args_by_name[arg.name] = evaluate_expression(ctx, arg.value, collector)
    return args_by_name


def _build_input_payload(signature: ir.FunctionSignature, args_by_name: dict[str, object], expr: ir.CallFlowExpr) -> dict[str, object]:
    payload: dict[str, object] = {}
    for param in signature.inputs:
        if param.name not in args_by_name:
            if param.required:
                raise Namel3ssError(
                    f"Missing flow input '{param.name}'",
                    line=expr.line,
                    column=expr.column,
                )
            continue
        value = args_by_name[param.name]
        require_type(value, param.type_name, line=expr.line, column=expr.column)
        payload[param.name] = value
    extra_args = set(args_by_name.keys()) - {param.name for param in signature.inputs}
    if extra_args:
        name = sorted(extra_args)[0]
        raise Namel3ssError(
            f"Unknown flow input '{name}'",
            line=expr.line,
            column=expr.column,
        )
    return payload


def _validate_flow_output(signature: ir.FunctionSignature, value: object, expr: ir.CallFlowExpr) -> dict:
    if not isinstance(value, dict):
        raise Namel3ssError(
            "Flow return must be a map",
            line=expr.line,
            column=expr.column,
        )
    output_map: dict = dict(value)
    expected = {param.name: param for param in signature.outputs or []}
    for name, param in expected.items():
        if name not in output_map:
            if not param.required:
                continue
            raise Namel3ssError(
                f"Missing flow output '{name}'",
                line=expr.line,
                column=expr.column,
            )
        require_type(output_map[name], param.type_name, line=expr.line, column=expr.column)
    extra_keys = set(output_map.keys()) - set(expected.keys())
    if extra_keys:
        name = sorted(extra_keys)[0]
        raise Namel3ssError(
            f"Unknown flow output '{name}'",
            line=expr.line,
            column=expr.column,
        )
    return output_map


def _select_outputs(output_map: dict, output_names: list[str], expr: ir.CallFlowExpr) -> dict:
    selected: dict[str, object] = {}
    for name in output_names:
        if name not in output_map:
            raise Namel3ssError(
                f"Missing flow output '{name}'",
                line=expr.line,
                column=expr.column,
            )
        selected[name] = output_map[name]
    return selected


def _lookup_flow(ctx: ExecutionContext, flow_name: str, *, line: int | None, column: int | None) -> ir.Flow:
    flow = ctx.flow_map.get(flow_name)
    if flow is not None:
        return flow
    flow_names = list(ctx.flow_map.keys())
    suggestion = difflib.get_close_matches(flow_name, flow_names, n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    raise Namel3ssError(
        build_guidance_message(
            what=f'Unknown flow "{flow_name}".{hint}',
            why="Flow calls must reference declared flows.",
            fix="Update the call to an existing flow.",
            example=f'flow "{flow_name}":\n  return "ok"',
        ),
        line=line,
        column=column,
    )


def _lookup_flow_contract(ctx: ExecutionContext, flow_name: str, *, line: int | None, column: int | None) -> ir.ContractDecl:
    contract = ctx.flow_contracts.get(flow_name)
    if contract is not None:
        return contract
    raise Namel3ssError(
        build_guidance_message(
            what=f'Flow "{flow_name}" is missing a contract.',
            why="Composed flows require explicit input and output contracts.",
            fix="Add a contract flow block for the called flow.",
            example=(
                f'contract flow "{flow_name}":\n  input:\n    value is text\n  output:\n    result is text'
            ),
        ),
        line=line,
        column=column,
    )


def _next_flow_call_id(ctx: ExecutionContext) -> str:
    counter = getattr(ctx, "flow_call_counter", 0) + 1
    setattr(ctx, "flow_call_counter", counter)
    return f"flow_call:{counter:04d}"


def _record_flow_call_started(
    ctx: ExecutionContext,
    flow_call_id: str,
    caller_flow: str | None,
    callee_flow: str,
    expr: ir.CallFlowExpr,
    contract_inputs: list[str],
    contract_outputs: list[str],
) -> None:
    ctx.traces.append(
        {
            "type": TraceEventType.FLOW_CALL_STARTED,
            "flow_call_id": flow_call_id,
            "caller_flow": caller_flow,
            "callee_flow": callee_flow,
            "inputs": [arg.name for arg in expr.arguments],
            "outputs": list(expr.outputs),
            "contract_inputs": list(contract_inputs),
            "contract_outputs": list(contract_outputs),
        }
    )


def _record_flow_call_finished(
    ctx: ExecutionContext,
    flow_call_id: str,
    caller_flow: str | None,
    callee_flow: str,
    *,
    status: str,
    error: Exception | None,
    contract_inputs: list[str],
    contract_outputs: list[str],
) -> None:
    event = {
        "type": TraceEventType.FLOW_CALL_FINISHED,
        "flow_call_id": flow_call_id,
        "caller_flow": caller_flow,
        "callee_flow": callee_flow,
        "status": status,
        "contract_inputs": list(contract_inputs),
        "contract_outputs": list(contract_outputs),
    }
    if error is not None:
        event["error_message"] = str(error)
    ctx.traces.append(event)


__all__ = ["execute_flow_call"]

from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.flow_contract import parse_selector_expression
from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.executor.stmt.records import execute_create, execute_update, execute_delete
from namel3ss.runtime.flow.gates import evaluate_requires
from namel3ss.runtime.flow.ids import flow_id, flow_step_id
from namel3ss.runtime.values.coerce import require_type
from namel3ss.traces.schema import TraceEventType


def run_declarative_flow(ctx: ExecutionContext) -> None:
    flow = ctx.flow
    steps = list(getattr(flow, "steps", None) or [])
    flow_id_value = flow_id(flow.name)
    _record_flow_start(ctx, flow_id_value, flow.name)
    input_fields = _collect_input_fields(steps)
    _validate_input_payload(ctx, input_fields)
    active_gate: dict | None = None
    for ordinal, step in enumerate(steps, start=1):
        step_kind = _step_kind(step)
        step_id = flow_step_id(flow.name, step_kind, ordinal)
        if active_gate and active_gate.get("status") == "blocked" and not isinstance(step, ir.FlowRequire):
            _record_flow_step(
                ctx,
                flow_id_value,
                flow.name,
                step_id,
                step_kind,
                ordinal,
                _what_for_step(step),
                status="skipped",
                gate=dict(active_gate),
                changes=None,
                fields=_input_fields_for_step(step),
            )
            continue
        if isinstance(step, ir.FlowInput):
            _record_flow_step(
                ctx,
                flow_id_value,
                flow.name,
                step_id,
                step_kind,
                ordinal,
                _what_for_step(step),
                status="ran",
                gate=dict(active_gate) if active_gate else None,
                changes=None,
                fields=_input_fields_for_step(step),
            )
            continue
        if isinstance(step, ir.FlowRequire):
            evaluation = evaluate_requires(step.condition, ctx.state)
            active_gate = _gate_payload(step.condition, evaluation)
            _record_flow_step(
                ctx,
                flow_id_value,
                flow.name,
                step_id,
                step_kind,
                ordinal,
                _what_for_step(step),
                status="ran",
                gate=dict(active_gate),
                changes=None,
                fields=None,
            )
            continue
        if isinstance(step, ir.FlowCreate):
            stmt = _build_create_stmt(step)
            ctx.current_statement = stmt
            ctx.current_statement_index = ordinal
            execute_create(ctx, stmt)
            _record_flow_step(
                ctx,
                flow_id_value,
                flow.name,
                step_id,
                step_kind,
                ordinal,
                _what_for_step(step),
                status="ran",
                gate=dict(active_gate) if active_gate else None,
                changes=_changes_payload(step.record_name, [field.name for field in step.fields]),
                fields=None,
            )
            continue
        if isinstance(step, ir.FlowUpdate):
            stmt = _build_update_stmt(step)
            ctx.current_statement = stmt
            ctx.current_statement_index = ordinal
            execute_update(ctx, stmt, deterministic=True)
            _record_flow_step(
                ctx,
                flow_id_value,
                flow.name,
                step_id,
                step_kind,
                ordinal,
                _what_for_step(step),
                status="ran",
                gate=dict(active_gate) if active_gate else None,
                changes=_changes_payload(step.record_name, [field.name for field in step.updates]),
                fields=None,
            )
            continue
        if isinstance(step, ir.FlowDelete):
            stmt = _build_delete_stmt(step)
            ctx.current_statement = stmt
            ctx.current_statement_index = ordinal
            execute_delete(ctx, stmt, deterministic=True)
            _record_flow_step(
                ctx,
                flow_id_value,
                flow.name,
                step_id,
                step_kind,
                ordinal,
                _what_for_step(step),
                status="ran",
                gate=dict(active_gate) if active_gate else None,
                changes=_changes_payload(step.record_name, []),
                fields=None,
            )
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Flow step type is not supported.",
                why="Declarative flows only allow input, require, create, update, and delete steps.",
                fix="Use one of the supported declarative steps.",
                example='flow "demo"\\n  input\\n    name is text',
            ),
            line=getattr(step, "line", None),
            column=getattr(step, "column", None),
        )


def _record_flow_start(ctx: ExecutionContext, flow_id_value: str, flow_name: str) -> None:
    ctx.traces.append(
        {
            "type": TraceEventType.FLOW_START,
            "flow_id": flow_id_value,
            "flow_name": flow_name,
        }
    )


def _record_flow_step(
    ctx: ExecutionContext,
    flow_id_value: str,
    flow_name: str,
    step_id: str,
    step_kind: str,
    ordinal: int,
    what: str,
    *,
    status: str,
    gate: dict | None,
    changes: dict | None,
    fields: list[str] | None,
) -> None:
    entry = {
        "type": TraceEventType.FLOW_STEP,
        "flow_id": flow_id_value,
        "flow_name": flow_name,
        "step_id": step_id,
        "step_kind": step_kind,
        "ordinal": ordinal,
        "what": what,
        "why": _why_for_step(ctx, flow_name),
        "status": status,
    }
    if gate:
        entry["gate"] = gate
    if changes:
        entry["changes"] = changes
    if fields is not None:
        entry["fields"] = list(fields)
    ctx.traces.append(entry)


def _collect_input_fields(steps: list[ir.FlowStep]) -> list[ir.FlowInputField]:
    for step in steps:
        if isinstance(step, ir.FlowInput):
            return list(step.fields)
    return []


def _validate_input_payload(ctx: ExecutionContext, fields: list[ir.FlowInputField]) -> None:
    if not fields:
        return
    payload = ctx.locals.get("input")
    if not isinstance(payload, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Flow input payload is not a JSON object.",
                why="Declarative flows expect input to be a dictionary of field values.",
                fix="Provide a JSON object with the required fields.",
                example='{"name":"Ada"}',
            )
        )
    for field in fields:
        if field.name not in payload:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Flow input is missing '{field.name}'.",
                    why="Declarative flow inputs are required.",
                    fix="Provide the missing field in the input payload.",
                    example=f'{{"{field.name}":"value"}}',
                ),
                line=field.line,
                column=field.column,
            )
        require_type(payload.get(field.name), field.type_name, line=field.line, column=field.column)


def _gate_payload(condition: str, evaluation) -> dict:
    status = "unknown"
    if evaluation.ready is True:
        status = "passed"
    elif evaluation.ready is False:
        status = "blocked"
    gate = {"requires": condition, "status": status, "reason": f"requires {condition}"}
    if evaluation.path:
        gate["path"] = list(evaluation.path)
    return gate


def _what_for_step(step: ir.FlowStep) -> str:
    if isinstance(step, ir.FlowInput):
        return "input"
    if isinstance(step, ir.FlowRequire):
        return f'require "{step.condition}"'
    if isinstance(step, ir.FlowCreate):
        return f'create "{step.record_name}"'
    if isinstance(step, ir.FlowUpdate):
        return f'update "{step.record_name}"'
    if isinstance(step, ir.FlowDelete):
        return f'delete "{step.record_name}"'
    return "step"


def _why_for_step(ctx: ExecutionContext, flow_name: str) -> str:
    action_id = getattr(ctx, "flow_action_id", None)
    if action_id:
        return f'action "{action_id}" ran flow "{flow_name}"'
    return f'flow "{flow_name}" ran'


def _changes_payload(record_name: str, fields: list[str]) -> dict:
    return {"record": record_name, "fields": list(fields)}


def _step_kind(step: ir.FlowStep) -> str:
    if isinstance(step, ir.FlowInput):
        return "input"
    if isinstance(step, ir.FlowRequire):
        return "require"
    if isinstance(step, ir.FlowCreate):
        return "create"
    if isinstance(step, ir.FlowUpdate):
        return "update"
    if isinstance(step, ir.FlowDelete):
        return "delete"
    return "step"


def _build_create_stmt(step: ir.FlowCreate) -> ir.Create:
    entries = [
        ir.MapEntry(
            key=ir.Literal(value=field.name, line=field.line, column=field.column),
            value=field.value,
            line=field.line,
            column=field.column,
        )
        for field in step.fields
    ]
    values = ir.MapExpr(entries=entries, line=step.line, column=step.column)
    return ir.Create(
        record_name=step.record_name,
        values=values,
        target="_",
        line=step.line,
        column=step.column,
    )


def _build_update_stmt(step: ir.FlowUpdate) -> ir.Update:
    if not step.selector:
        raise Namel3ssError(
            build_guidance_message(
                what="Update step is missing a where selector.",
                why="Declarative updates require a selector to target records.",
                fix='Add a where line like `where "id is 1"`.',
                example='update "Order"\\n  where "id is 1"\\n  set\\n    status is "shipped"',
            ),
            line=step.line,
            column=step.column,
        )
    predicate = parse_selector_expression(step.selector, line=step.line, column=step.column)
    updates = [
        ir.UpdateField(name=field.name, expression=field.value, line=field.line, column=field.column)
        for field in step.updates
    ]
    return ir.Update(
        record_name=step.record_name,
        predicate=predicate,
        updates=updates,
        line=step.line,
        column=step.column,
    )


def _build_delete_stmt(step: ir.FlowDelete) -> ir.Delete:
    if not step.selector:
        raise Namel3ssError(
            build_guidance_message(
                what="Delete step is missing a where selector.",
                why="Declarative deletes require a selector to target records.",
                fix='Add a where line like `where "id is 1"`.',
                example='delete "Order"\\n  where "id is 1"',
            ),
            line=step.line,
            column=step.column,
        )
    predicate = parse_selector_expression(step.selector, line=step.line, column=step.column)
    return ir.Delete(
        record_name=step.record_name,
        predicate=predicate,
        line=step.line,
        column=step.column,
    )


def _input_fields_for_step(step: ir.FlowStep) -> list[str] | None:
    if not isinstance(step, ir.FlowInput):
        return None
    return [field.name for field in step.fields]


__all__ = ["run_declarative_flow"]

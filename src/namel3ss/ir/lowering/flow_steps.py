from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.ir.model import flow_steps as ir_steps


def lower_flow_steps(steps: list[ast.FlowStep] | None) -> list[ir_steps.FlowStep] | None:
    if not steps:
        return None
    lowered: list[ir_steps.FlowStep] = []
    for step in steps:
        if isinstance(step, ast.FlowInput):
            lowered.append(
                ir_steps.FlowInput(
                    fields=[_lower_input_field(field) for field in step.fields],
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        if isinstance(step, ast.FlowRequire):
            lowered.append(ir_steps.FlowRequire(condition=step.condition, line=step.line, column=step.column))
            continue
        if isinstance(step, ast.FlowCreate):
            lowered.append(
                ir_steps.FlowCreate(
                    record_name=step.record_name,
                    fields=[_lower_flow_field(field) for field in step.fields],
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        if isinstance(step, ast.FlowUpdate):
            lowered.append(
                ir_steps.FlowUpdate(
                    record_name=step.record_name,
                    selector=step.selector,
                    updates=[_lower_flow_field(field) for field in step.updates],
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        if isinstance(step, ast.FlowDelete):
            lowered.append(
                ir_steps.FlowDelete(
                    record_name=step.record_name,
                    selector=step.selector,
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        raise TypeError(f"Unhandled flow step type: {type(step)}")
    return lowered


def _lower_input_field(field: ast.FlowInputField) -> ir_steps.FlowInputField:
    return ir_steps.FlowInputField(
        name=field.name,
        type_name=field.type_name,
        type_was_alias=field.type_was_alias,
        raw_type_name=field.raw_type_name,
        type_line=field.type_line,
        type_column=field.type_column,
        line=field.line,
        column=field.column,
    )


def _lower_flow_field(field: ast.FlowField) -> ir_steps.FlowField:
    return ir_steps.FlowField(
        name=field.name,
        value=_lower_expression(field.value),
        line=field.line,
        column=field.column,
    )


__all__ = ["lower_flow_steps"]

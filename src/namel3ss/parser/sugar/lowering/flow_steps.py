from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.parser.sugar.lowering.expressions import _lower_expression


def _lower_flow_steps(steps: list[ast.FlowStep] | None) -> list[ast.FlowStep] | None:
    if not steps:
        return None
    lowered: list[ast.FlowStep] = []
    for step in steps:
        if isinstance(step, ast.FlowInput):
            lowered.append(
                ast.FlowInput(
                    fields=[_lower_input_field(field) for field in step.fields],
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        if isinstance(step, ast.FlowRequire):
            lowered.append(ast.FlowRequire(condition=step.condition, line=step.line, column=step.column))
            continue
        if isinstance(step, ast.FlowCreate):
            lowered.append(
                ast.FlowCreate(
                    record_name=step.record_name,
                    fields=[_lower_flow_field(field) for field in step.fields],
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        if isinstance(step, ast.FlowUpdate):
            lowered.append(
                ast.FlowUpdate(
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
                ast.FlowDelete(
                    record_name=step.record_name,
                    selector=step.selector,
                    line=step.line,
                    column=step.column,
                )
            )
            continue
        raise TypeError(f"Unhandled flow step type: {type(step)}")
    return lowered


def _lower_input_field(field: ast.FlowInputField) -> ast.FlowInputField:
    return ast.FlowInputField(
        name=field.name,
        type_name=field.type_name,
        type_was_alias=field.type_was_alias,
        raw_type_name=field.raw_type_name,
        type_line=field.type_line,
        type_column=field.type_column,
        line=field.line,
        column=field.column,
    )


def _lower_flow_field(field: ast.FlowField) -> ast.FlowField:
    return ast.FlowField(
        name=field.name,
        value=_lower_expression(field.value),
        line=field.line,
        column=field.column,
    )


__all__ = ["_lower_flow_steps"]

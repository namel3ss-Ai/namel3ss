from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.utils.numbers import is_number, to_decimal
from namel3ss.validation import ValidationMode


def select_status_items(
    status_block: ir.StatusBlock | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    *,
    line: int | None,
    column: int | None,
) -> list[ir.PageItem] | None:
    if status_block is None:
        return None
    if not isinstance(status_block, ir.StatusBlock):
        raise Namel3ssError("Status block is invalid.", line=line, column=column)
    matches: list[ir.StatusCase] = []
    for case in status_block.cases:
        if _evaluate_status_condition(case.condition, state_ctx, line=case.line, column=case.column):
            matches.append(case)
    if len(matches) > 1:
        names = ", ".join(case.name for case in matches)
        raise Namel3ssError(
            f"Status block matches multiple entries: {names}.",
            line=status_block.line,
            column=status_block.column,
        )
    if matches:
        return matches[0].items
    return None


def _evaluate_status_condition(
    condition: ir.StatusCondition,
    state_ctx: StateContext,
    *,
    line: int | None,
    column: int | None,
) -> bool:
    if not isinstance(condition, ir.StatusCondition):
        raise Namel3ssError("Status condition is invalid.", line=line, column=column)
    path = getattr(condition.path, "path", None)
    if not isinstance(condition.path, ir.StatePath) or not path:
        raise Namel3ssError("Status condition requires state.<path> is <value>.", line=line, column=column)
    label = f"state.{'.'.join(path)}"
    if not state_ctx.declared(path):
        raise Namel3ssError(
            f"Status condition requires declared state path '{label}'.",
            line=line,
            column=column,
        )
    try:
        state_value, _ = state_ctx.value(path, default=None, register_default=False)
    except KeyError as err:
        raise Namel3ssError(
            f"Status condition requires declared state path '{label}'.",
            line=line,
            column=column,
        ) from err
    if condition.kind == "empty":
        if isinstance(state_value, (list, tuple, dict, set)):
            return len(state_value) == 0
        raise Namel3ssError(
            _status_empty_type_mismatch(label, state_value),
            line=line,
            column=column,
        )
    if condition.kind == "equals":
        literal = condition.value
        if not isinstance(literal, ir.Literal):
            raise Namel3ssError(
                "Status condition requires a text, number, or boolean value.",
                line=line,
                column=column,
            )
        return _evaluate_equals(label, state_value, literal.value, line=line, column=column)
    raise Namel3ssError("Status condition only supports equality or empty checks.", line=line, column=column)


def _evaluate_equals(label: str, state_value: object, literal_value: object, *, line: int | None, column: int | None) -> bool:
    if isinstance(literal_value, bool):
        if not isinstance(state_value, bool):
            raise Namel3ssError(
                _status_type_mismatch(label, "boolean", state_value),
                line=line,
                column=column,
            )
        return state_value is literal_value
    if is_number(literal_value):
        if not is_number(state_value):
            raise Namel3ssError(
                _status_type_mismatch(label, "number", state_value),
                line=line,
                column=column,
            )
        return to_decimal(state_value) == to_decimal(literal_value)
    if isinstance(literal_value, str):
        if not isinstance(state_value, str):
            raise Namel3ssError(
                _status_type_mismatch(label, "text", state_value),
                line=line,
                column=column,
            )
        return state_value == literal_value
    raise Namel3ssError(
        "Status condition requires a text, number, or boolean value.",
        line=line,
        column=column,
    )


def _status_type_mismatch(label: str, expected: str, actual_value: object) -> str:
    actual = type_name_for_value(actual_value)
    return f"Status condition for {label} expects {expected} but state value is {actual}."


def _status_empty_type_mismatch(label: str, actual_value: object) -> str:
    actual = type_name_for_value(actual_value)
    return f"Status condition for {label} expects a list or map but state value is {actual}."


__all__ = ["select_status_items"]

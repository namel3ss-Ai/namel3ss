from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.utils.numbers import decimal_to_str, is_number, to_decimal
from namel3ss.validation import ValidationMode


def evaluate_visibility(
    visibility: ir.StatePath | None,
    visibility_rule: ir.VisibilityRule | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    *,
    line: int | None,
    column: int | None,
) -> tuple[bool, dict | None]:
    if visibility is None and visibility_rule is None:
        return True, None
    if visibility is not None and visibility_rule is not None:
        raise Namel3ssError(
            "Visibility cannot combine visibility clauses with only-when rules.",
            line=line,
            column=column,
        )
    if visibility_rule is not None:
        if not isinstance(visibility_rule, ir.VisibilityRule):
            raise Namel3ssError("Visibility rule requires state.<path> is <value>.", line=line, column=column)
        path = getattr(visibility_rule.path, "path", None)
        if not isinstance(visibility_rule.path, ir.StatePath) or not path:
            raise Namel3ssError("Visibility rule requires state.<path> is <value>.", line=line, column=column)
        label = f"state.{'.'.join(path)}"
        if not state_ctx.declared(path):
            raise Namel3ssError(
                f"Visibility rule requires declared state path '{label}'.",
                line=line,
                column=column,
            )
        try:
            state_value, _ = state_ctx.value(path, default=None, register_default=False)
        except KeyError as err:
            raise Namel3ssError(
                f"Visibility rule requires declared state path '{label}'.",
                line=line,
                column=column,
            ) from err
        literal = visibility_rule.value
        if not isinstance(literal, ir.Literal):
            raise Namel3ssError("Visibility rule requires a text, number, or boolean value.", line=line, column=column)
        result = _evaluate_visibility_rule(label, state_value, literal.value, line=line, column=column)
        predicate = f"{label} is {_format_visibility_value(literal.value)}"
        info = {"predicate": predicate, "state_paths": [label], "result": result}
        return result, info
    if visibility is None:
        return True, None
    if not isinstance(visibility, ir.StatePath) or not visibility.path:
        raise Namel3ssError("Visibility requires state.<path>.", line=line, column=column)
    path = visibility.path
    label = f"state.{'.'.join(path)}"
    result = False
    if state_ctx.has_value(path):
        value, _ = state_ctx.value(path, default=None, register_default=False)
        result = bool(value)
    info = {"predicate": label, "state_paths": [label], "result": result}
    return result, info


def _evaluate_visibility_rule(label: str, state_value: object, literal_value: object, *, line: int | None, column: int | None) -> bool:
    if isinstance(literal_value, bool):
        if not isinstance(state_value, bool):
            raise Namel3ssError(
                _visibility_type_mismatch(label, "boolean", state_value),
                line=line,
                column=column,
            )
        return state_value is literal_value
    if is_number(literal_value):
        if not is_number(state_value):
            raise Namel3ssError(
                _visibility_type_mismatch(label, "number", state_value),
                line=line,
                column=column,
            )
        return to_decimal(state_value) == to_decimal(literal_value)
    if isinstance(literal_value, str):
        if not isinstance(state_value, str):
            raise Namel3ssError(
                _visibility_type_mismatch(label, "text", state_value),
                line=line,
                column=column,
            )
        return state_value == literal_value
    raise Namel3ssError(
        "Visibility rule requires a text, number, or boolean value.",
        line=line,
        column=column,
    )


def _visibility_type_mismatch(label: str, expected: str, actual_value: object) -> str:
    actual = type_name_for_value(actual_value)
    return f"Visibility rule for {label} expects {expected} but state value is {actual}."


def _format_visibility_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        if isinstance(value, Decimal):
            return decimal_to_str(value)
        return str(value)
    if isinstance(value, str):
        return f"\"{value}\""
    return str(value)


def apply_visibility(element: dict, visible: bool, info: dict | None) -> dict:
    if info is not None:
        element["visibility"] = info
        element["visible"] = bool(visible)
        return element
    if not visible:
        element["visible"] = False
    return element


__all__ = ["apply_visibility", "evaluate_visibility"]

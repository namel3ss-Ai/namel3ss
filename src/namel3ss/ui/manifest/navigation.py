from __future__ import annotations

from decimal import Decimal

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.utils.numbers import decimal_to_str, is_number, to_decimal


def select_active_page(
    rules: list[ir.ActivePageRule] | None,
    *,
    pages: list[dict],
    state_ctx: StateContext,
) -> dict | None:
    if not rules:
        return None
    if not pages:
        raise Namel3ssError("Active page rules require at least one page.")
    page_by_name = {page.get("name"): page for page in pages if page.get("name")}
    for rule in rules:
        if not isinstance(rule, ir.ActivePageRule):
            raise Namel3ssError(
                "Active page rules require: is \"<page>\" only when state.<path> is <value>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        path = getattr(rule.path, "path", None)
        if not isinstance(rule.path, ir.StatePath) or not path:
            raise Namel3ssError(
                "Active page rules require state.<path> is <value>.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        label = f"state.{'.'.join(path)}"
        if not state_ctx.declared(path):
            raise Namel3ssError(
                f"Active page rules require declared state path '{label}'.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        try:
            state_value, _ = state_ctx.value(path, default=None, register_default=False)
        except KeyError as err:
            raise Namel3ssError(
                f"Active page rules require declared state path '{label}'.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            ) from err
        literal = rule.value
        if not isinstance(literal, ir.Literal):
            raise Namel3ssError(
                "Active page rules require a text, number, or boolean value.",
                line=getattr(rule, "line", None),
                column=getattr(rule, "column", None),
            )
        result = _evaluate_equals(label, state_value, literal.value, line=rule.line, column=rule.column)
        if result:
            selected_page = page_by_name.get(rule.page_name)
            if not selected_page:
                raise Namel3ssError(
                    f"Active page rule references unknown page '{rule.page_name}'.",
                    line=getattr(rule, "line", None),
                    column=getattr(rule, "column", None),
                )
            return {
                "active_page": {
                    "name": selected_page.get("name", ""),
                    "slug": selected_page.get("slug", ""),
                    "source": "rule",
                    "predicate": f"{label} is {_format_value(literal.value)}",
                    "state_paths": [label],
                }
            }
    default_page = pages[0]
    return {
        "active_page": {
            "name": default_page.get("name", ""),
            "slug": default_page.get("slug", ""),
            "source": "default",
        }
    }


def _evaluate_equals(label: str, state_value: object, literal_value: object, *, line: int | None, column: int | None) -> bool:
    if isinstance(literal_value, bool):
        if not isinstance(state_value, bool):
            raise Namel3ssError(
                _type_mismatch(label, "boolean", state_value),
                line=line,
                column=column,
            )
        return state_value is literal_value
    if is_number(literal_value):
        if not is_number(state_value):
            raise Namel3ssError(
                _type_mismatch(label, "number", state_value),
                line=line,
                column=column,
            )
        return to_decimal(state_value) == to_decimal(literal_value)
    if isinstance(literal_value, str):
        if not isinstance(state_value, str):
            raise Namel3ssError(
                _type_mismatch(label, "text", state_value),
                line=line,
                column=column,
            )
        return state_value == literal_value
    raise Namel3ssError(
        "Active page rules require a text, number, or boolean value.",
        line=line,
        column=column,
    )


def _type_mismatch(label: str, expected: str, actual_value: object) -> str:
    actual = type_name_for_value(actual_value)
    return f"Active page rule for {label} expects {expected} but state value is {actual}."


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        if isinstance(value, Decimal):
            return decimal_to_str(value)
        return str(value)
    if isinstance(value, str):
        return f"\"{value}\""
    return str(value)


__all__ = ["select_active_page"]

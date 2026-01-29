from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ui.manifest.state_defaults import StateContext
from namel3ss.validation import ValidationMode


def evaluate_visibility(
    visibility: ir.StatePath | None,
    state_ctx: StateContext,
    mode: ValidationMode,
    warnings: list | None,
    *,
    line: int | None,
    column: int | None,
) -> tuple[bool, dict | None]:
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


def apply_visibility(element: dict, visible: bool, info: dict | None) -> dict:
    if info is not None:
        element["visibility"] = info
        element["visible"] = bool(visible)
        return element
    if not visible:
        element["visible"] = False
    return element


__all__ = ["apply_visibility", "evaluate_visibility"]

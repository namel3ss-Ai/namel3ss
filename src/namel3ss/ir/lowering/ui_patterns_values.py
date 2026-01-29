from __future__ import annotations

from typing import Iterable

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.patterns.model import PatternDefinition


def resolve_visibility(
    value: ast.StatePath | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> ast.StatePath | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"state"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if not isinstance(resolved, ast.StatePath):
        raise Namel3ssError("Visibility requires state.<path>.", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return resolved


def resolve_text(
    value: str | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> str | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"text"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if not isinstance(resolved, str):
        raise Namel3ssError("Expected text", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return resolved


def resolve_text_optional(
    value: str | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> str | None:
    if value is None:
        return None
    return resolve_text(value, param_values=param_values, param_defs=param_defs)


def resolve_boolean_optional(
    value: bool | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> bool | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"boolean"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if not isinstance(resolved, bool):
        raise Namel3ssError("Expected boolean", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return resolved


def resolve_number_optional(
    value: int | float | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> float | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"number"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float)):
        raise Namel3ssError("Expected number", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return float(resolved)


def resolve_record(
    value: str | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> str | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"record"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if not isinstance(resolved, str):
        raise Namel3ssError("Expected record name", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return resolved


def resolve_record_optional(
    value: str | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> str | None:
    if value is None:
        return None
    return resolve_record(value, param_values=param_values, param_defs=param_defs)


def resolve_page(
    value: str | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> str | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"page", "text"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if not isinstance(resolved, str):
        raise Namel3ssError("Expected page name", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return resolved


def resolve_page_optional(
    value: str | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> str | None:
    if value is None:
        return None
    return resolve_page(value, param_values=param_values, param_defs=param_defs)

def resolve_state(
    value: ast.StatePath | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> ast.StatePath | None:
    if value is None:
        return None
    resolved = resolve_param_ref(value, expected_kinds={"state"}, param_values=param_values, param_defs=param_defs)
    if resolved is None:
        return None
    if not isinstance(resolved, ast.StatePath):
        raise Namel3ssError("Expected state path", line=getattr(value, "line", None), column=getattr(value, "column", None))
    return resolved


def resolve_state_optional(
    value: ast.StatePath | ast.PatternParamRef | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> ast.StatePath | None:
    if value is None:
        return None
    return resolve_state(value, param_values=param_values, param_defs=param_defs)


def resolve_param_ref(
    value: object,
    *,
    expected_kinds: set[str],
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
) -> object:
    if not isinstance(value, ast.PatternParamRef):
        return value
    if param_values is None or param_defs is None:
        raise Namel3ssError("Pattern parameters are only available inside patterns", line=value.line, column=value.column)
    param = param_defs.get(value.name)
    if param is None:
        raise Namel3ssError(
            f"Pattern parameter '{value.name}' is not declared",
            line=value.line,
            column=value.column,
        )
    if param.kind not in expected_kinds:
        expected = ", ".join(sorted(expected_kinds))
        raise Namel3ssError(
            f"Pattern parameter '{value.name}' must be {expected}",
            line=value.line,
            column=value.column,
        )
    return param_values.get(value.name)


def resolve_pattern_params(
    pattern: PatternDefinition,
    arguments: list[ast.PatternArgument] | None,
    *,
    param_values: dict[str, object] | None,
    param_defs: dict[str, ast.PatternParam] | None,
    line: int | None,
    column: int | None,
) -> dict[str, object]:
    defs = {param.name: param for param in pattern.parameters}
    provided: dict[str, object] = {}
    if arguments:
        for arg in arguments:
            param = defs.get(arg.name)
            if param is None:
                raise Namel3ssError(
                    f"Pattern argument '{arg.name}' is not declared on pattern '{pattern.name}'",
                    line=arg.line,
                    column=arg.column,
                )
            value = arg.value
            if isinstance(value, ast.PatternParamRef):
                if param_values is None or param_defs is None:
                    raise Namel3ssError("Pattern arguments cannot reference parameters", line=arg.line, column=arg.column)
                outer = param_defs.get(value.name)
                if outer is None:
                    raise Namel3ssError(
                        f"Pattern parameter '{value.name}' is not declared",
                        line=value.line,
                        column=value.column,
                    )
                if outer.kind != param.kind:
                    raise Namel3ssError(
                        f"Pattern argument '{arg.name}' must be {param.kind}",
                        line=arg.line,
                        column=arg.column,
                    )
                value = param_values.get(value.name)
            if value is not None and not value_matches_kind(value, param.kind):
                raise Namel3ssError(
                    f"Pattern argument '{arg.name}' must be {param.kind}",
                    line=arg.line,
                    column=arg.column,
                )
            provided[arg.name] = value
    values: dict[str, object] = {}
    for param in pattern.parameters:
        if param.name in provided:
            value = provided[param.name]
            if value is None and not param.optional and param.default is None:
                raise Namel3ssError(
                    f"Pattern parameter '{param.name}' is required for pattern '{pattern.name}'",
                    line=line,
                    column=column,
                )
            values[param.name] = value
            continue
        if param.default is not None:
            values[param.name] = param.default
            continue
        if param.optional:
            values[param.name] = None
            continue
        raise Namel3ssError(
            f"Pattern parameter '{param.name}' is required for pattern '{pattern.name}'",
            line=line,
            column=column,
        )
    return values


def value_matches_kind(value: object, kind: str) -> bool:
    if kind in {"text", "record", "page"}:
        return isinstance(value, str)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    return False


def qualify_name(value: str, context_module: str | None, known: Iterable[str]) -> str:
    if "." in value or not context_module:
        return value
    candidate = f"{context_module}.{value}"
    if candidate in set(known):
        return candidate
    return value


__all__ = [
    "qualify_name",
    "resolve_boolean_optional",
    "resolve_number_optional",
    "resolve_param_ref",
    "resolve_pattern_params",
    "resolve_page",
    "resolve_page_optional",
    "resolve_record",
    "resolve_record_optional",
    "resolve_state",
    "resolve_state_optional",
    "resolve_text",
    "resolve_text_optional",
    "resolve_visibility",
    "value_matches_kind",
]

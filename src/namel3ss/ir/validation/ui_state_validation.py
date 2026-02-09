from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Iterable

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.model.ui_state import iter_ui_state_fields


_SCOPE_ORDER = ("ephemeral", "session", "persistent")


def lower_ui_state_declaration(declaration: ast.UIStateDecl | None) -> ir.UIStateDecl | None:
    if declaration is None:
        return None
    if not isinstance(declaration, ast.UIStateDecl):
        raise Namel3ssError(
            "ui_state must declare scopes: ephemeral, session, persistent.",
            line=getattr(declaration, "line", None),
            column=getattr(declaration, "column", None),
        )
    seen_keys: dict[str, str] = {}
    lowered_by_scope: dict[str, list[ir.UIStateField]] = {scope: [] for scope in _SCOPE_ORDER}
    for scope in _SCOPE_ORDER:
        raw_fields = getattr(declaration, scope, None) or []
        if not isinstance(raw_fields, list):
            raise Namel3ssError(
                f"ui_state scope '{scope}' must be a list of fields.",
                line=getattr(declaration, "line", None),
                column=getattr(declaration, "column", None),
            )
        for raw_field in raw_fields:
            if not isinstance(raw_field, ast.UIStateField):
                raise Namel3ssError(
                    "ui_state fields must use: <key> is <type>.",
                    line=getattr(raw_field, "line", None),
                    column=getattr(raw_field, "column", None),
                )
            key = str(getattr(raw_field, "key", "") or "")
            if not key:
                raise Namel3ssError(
                    "ui_state keys must be non-empty identifiers.",
                    line=raw_field.line,
                    column=raw_field.column,
                )
            if key in seen_keys:
                raise Namel3ssError(
                    f"ui_state key '{key}' is declared more than once (already in scope '{seen_keys[key]}').",
                    line=raw_field.line,
                    column=raw_field.column,
                )
            seen_keys[key] = scope
            type_name = str(getattr(raw_field, "type_name", "") or "")
            if not type_name:
                raise Namel3ssError(
                    f"ui_state key '{key}' must declare a type.",
                    line=raw_field.line,
                    column=raw_field.column,
                )
            lowered_by_scope[scope].append(
                ir.UIStateField(
                    key=key,
                    type_name=type_name,
                    raw_type_name=getattr(raw_field, "raw_type_name", None),
                    default_value=_default_value_for_type(type_name),
                    line=raw_field.line,
                    column=raw_field.column,
                )
            )
    if not any(lowered_by_scope[scope] for scope in _SCOPE_ORDER):
        raise Namel3ssError(
            "ui_state must declare at least one key.",
            line=declaration.line,
            column=declaration.column,
        )
    return ir.UIStateDecl(
        ephemeral=lowered_by_scope["ephemeral"],
        session=lowered_by_scope["session"],
        persistent=lowered_by_scope["persistent"],
        line=declaration.line,
        column=declaration.column,
    )


def validate_ui_state(
    program: ir.Program,
    declaration: ir.UIStateDecl | None,
    capabilities: tuple[str, ...],
) -> None:
    if declaration is None:
        return
    if "ui_state" not in set(capabilities or ()):
        raise Namel3ssError(
            "UI state requires capability ui_state. Add 'ui_state' to the capabilities list.",
            line=getattr(declaration, "line", None),
            column=getattr(declaration, "column", None),
        )
    declared_keys: set[str] = set()
    for _scope, field in iter_ui_state_fields(declaration):
        declared_keys.add(field.key)
    for path_node, is_write in _iter_program_state_paths(program):
        _validate_state_path(path_node, is_write=is_write, declared_keys=declared_keys)


def build_ui_state_defaults(declaration: ir.UIStateDecl | None) -> dict:
    if declaration is None:
        return {}
    ui_defaults: dict[str, object] = {}
    for _scope, field in iter_ui_state_fields(declaration):
        ui_defaults[field.key] = field.default_value
    if not ui_defaults:
        return {}
    return {"ui": ui_defaults}


def _validate_state_path(
    path_node: ir.StatePath,
    *,
    is_write: bool,
    declared_keys: set[str],
) -> None:
    path = list(getattr(path_node, "path", []) or [])
    if not path:
        return
    if path[0] != "ui":
        return
    label = f"state.{'.'.join(path)}"
    if len(path) < 2:
        action = "write to" if is_write else "read from"
        raise Namel3ssError(
            f"Cannot {action} '{label}'. ui_state must target state.ui.<key>.",
            line=path_node.line,
            column=path_node.column,
        )
    key = path[1]
    if key in declared_keys:
        return
    if is_write:
        raise Namel3ssError(
            (
                f"Write to undeclared ui_state key '{label}'. "
                f"Declare '{key}' in ui_state before writing to it."
            ),
            line=path_node.line,
            column=path_node.column,
        )
    raise Namel3ssError(
        (
            f"State reference '{label}' is not declared in ui_state. "
            f"Declare '{key}' in ui_state before reading it."
        ),
        line=path_node.line,
        column=path_node.column,
    )


def _iter_program_state_paths(program: ir.Program) -> Iterable[tuple[ir.StatePath, bool]]:
    for flow in getattr(program, "flows", []) or []:
        yield from _iter_state_paths(flow)
    for page in getattr(program, "pages", []) or []:
        yield from _iter_state_paths(page)
    for rule in getattr(program, "ui_active_page_rules", None) or []:
        yield from _iter_state_paths(rule)


def _iter_state_paths(value: object) -> Iterable[tuple[ir.StatePath, bool]]:
    if isinstance(value, ir.StatePath):
        yield value, False
        return
    if isinstance(value, ir.Set):
        if isinstance(value.target, ir.StatePath):
            yield value.target, True
        yield from _iter_state_paths(value.expression)
        return
    if isinstance(value, ir.OrderList):
        if isinstance(value.target, ir.StatePath):
            yield value.target, True
        return
    if isinstance(value, dict):
        for key in sorted(value.keys(), key=str):
            yield from _iter_state_paths(value[key])
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_state_paths(item)
        return
    if not is_dataclass(value):
        return
    for field in fields(value):
        if field.name in {"line", "column"}:
            continue
        yield from _iter_state_paths(getattr(value, field.name))


def _default_value_for_type(type_name: str) -> object:
    normalized = str(type_name or "").strip()
    if "|" in normalized:
        normalized = normalized.split("|", 1)[0].strip()
    lowered = normalized.lower()
    if lowered in {"text", "string"}:
        return ""
    if lowered in {"number", "int", "integer"}:
        return 0
    if lowered in {"boolean", "bool"}:
        return False
    if lowered == "null":
        return None
    if lowered.startswith("list<") or lowered == "list":
        return []
    if lowered.startswith("map<") or lowered in {"map", "json"}:
        return {}
    return {}


__all__ = ["build_ui_state_defaults", "lower_ui_state_declaration", "validate_ui_state"]

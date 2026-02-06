from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_BUILTIN_TYPES = {"text", "number", "boolean", "json"}


def validate_routes(
    routes: list[ast.RouteDefinition],
    *,
    record_names: set[str],
    flow_names: set[str],
) -> None:
    seen: dict[str, ast.RouteDefinition] = {}
    for route in routes:
        if route.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Route '{route.name}' is declared more than once.",
                    why="Each route name must be unique.",
                    fix="Rename or remove the duplicate route.",
                    example=f'route "{route.name}":',
                ),
                line=route.line,
                column=route.column,
            )
        seen[route.name] = route
        _validate_route(route, record_names=record_names, flow_names=flow_names)


def _validate_route(
    route: ast.RouteDefinition,
    *,
    record_names: set[str],
    flow_names: set[str],
) -> None:
    if not route.path:
        raise Namel3ssError("Route is missing a path", line=route.line, column=route.column)
    if not route.method:
        raise Namel3ssError("Route is missing a method", line=route.line, column=route.column)
    method = str(route.method).upper()
    if method not in _ALLOWED_METHODS:
        raise Namel3ssError(
            f"Unsupported HTTP method '{route.method}'.",
            line=route.line,
            column=route.column,
        )
    if not route.response:
        raise Namel3ssError("Route is missing a response block", line=route.line, column=route.column)
    if not route.request:
        raise Namel3ssError("Route is missing a request block", line=route.line, column=route.column)
    if not route.flow_name:
        raise Namel3ssError("Route is missing a flow", line=route.line, column=route.column)
    if route.flow_name not in flow_names:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Route '{route.name}' references unknown flow '{route.flow_name}'.",
                why="Routes must point to flows declared in the program.",
                fix="Update the route to use a defined flow or add the flow.",
                example=f'flow "{route.flow_name}"',
            ),
            line=route.line,
            column=route.column,
        )
    _validate_field_block(route.parameters or {}, record_names=record_names, route=route)
    _validate_field_block(route.request, record_names=record_names, route=route)
    _validate_field_block(route.response, record_names=record_names, route=route)


def _validate_field_block(
    fields: dict[str, ast.RouteField],
    *,
    record_names: set[str],
    route: ast.RouteDefinition,
) -> None:
    for field in fields.values():
        _validate_type(
            field.type_name,
            record_names=record_names,
            line=field.type_line or field.line or route.line,
            column=field.type_column or field.column or route.column,
        )


def _validate_type(
    type_name: str,
    *,
    record_names: set[str],
    line: int | None,
    column: int | None,
) -> None:
    if not isinstance(type_name, str) or not type_name:
        raise Namel3ssError("Route field type is missing", line=line, column=column)
    inner = _split_list_type(type_name)
    if inner is not None:
        _validate_type(inner, record_names=record_names, line=line, column=column)
        return
    if type_name in _BUILTIN_TYPES:
        return
    if type_name in record_names:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown route type '{type_name}'.",
            why="Route schemas may use built-in types or record references.",
            fix="Use text, number, boolean, json, list<type>, or a defined record.",
            example='response:\n  user is User',
        ),
        line=line,
        column=column,
    )


def _split_list_type(type_name: str) -> str | None:
    if not type_name.startswith("list<"):
        return None
    depth = 0
    start = None
    end = None
    for idx, ch in enumerate(type_name):
        if ch == "<":
            depth += 1
            if depth == 1:
                start = idx + 1
        elif ch == ">":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if start is None or end is None or end != len(type_name) - 1:
        return None
    inner = type_name[start:end].strip()
    if not inner:
        return None
    return inner


__all__ = ["validate_routes"]

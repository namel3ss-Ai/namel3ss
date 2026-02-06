from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.model.routes import RouteDefinition, RouteField


def lower_routes(routes: list[ast.RouteDefinition]) -> list[RouteDefinition]:
    return [_lower_route(route) for route in routes]


def _lower_route(route: ast.RouteDefinition) -> RouteDefinition:
    return RouteDefinition(
        name=route.name,
        path=route.path,
        method=route.method,
        parameters=_lower_field_map(route.parameters or {}),
        request=_lower_field_map(route.request) if route.request else None,
        response=_lower_field_map(route.response or {}),
        flow_name=route.flow_name,
        upload=route.upload,
        generated=bool(getattr(route, "generated", False)),
        line=route.line,
        column=route.column,
    )


def _lower_field_map(fields: dict[str, ast.RouteField] | None) -> dict[str, RouteField] | None:
    if fields is None:
        return None
    lowered: dict[str, RouteField] = {}
    for name, field in fields.items():
        lowered[name] = RouteField(
            name=field.name,
            type_name=field.type_name,
            type_was_alias=field.type_was_alias,
            raw_type_name=field.raw_type_name,
            type_line=field.type_line,
            type_column=field.type_column,
            line=field.line,
            column=field.column,
        )
    return lowered


__all__ = ["lower_routes"]

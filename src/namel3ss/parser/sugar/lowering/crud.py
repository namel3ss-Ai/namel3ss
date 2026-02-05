from __future__ import annotations

import re

from namel3ss.ast import nodes as ast


_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def expand_crud_routes(crud_defs: list[ast.CrudDefinition]) -> list[ast.RouteDefinition]:
    routes: list[ast.RouteDefinition] = []
    for crud in crud_defs:
        record_name = crud.record_name
        record_slug = _record_slug(record_name)
        collection = _pluralize(record_slug)
        routes.extend(
            [
                _build_crud_route(
                    name=f"create_{record_slug}",
                    method="POST",
                    path=f"/api/{collection}",
                    parameters=None,
                    request=_crud_request_fields(record_name, crud),
                    response=_crud_response_fields(record_slug, record_name, crud),
                    flow_name=f"create_{record_slug}",
                    crud=crud,
                ),
                _build_crud_route(
                    name=f"read_{record_slug}",
                    method="GET",
                    path=f"/api/{collection}/{{id}}",
                    parameters=_crud_id_params(crud),
                    request=_crud_id_request_fields(crud),
                    response=_crud_response_fields(record_slug, record_name, crud),
                    flow_name=f"read_{record_slug}",
                    crud=crud,
                ),
                _build_crud_route(
                    name=f"update_{record_slug}",
                    method="PUT",
                    path=f"/api/{collection}/{{id}}",
                    parameters=_crud_id_params(crud),
                    request=_crud_request_fields(record_name, crud),
                    response=_crud_response_fields(record_slug, record_name, crud),
                    flow_name=f"update_{record_slug}",
                    crud=crud,
                ),
                _build_crud_route(
                    name=f"delete_{record_slug}",
                    method="DELETE",
                    path=f"/api/{collection}/{{id}}",
                    parameters=_crud_id_params(crud),
                    request=_crud_id_request_fields(crud),
                    response=_crud_response_fields(record_slug, record_name, crud),
                    flow_name=f"delete_{record_slug}",
                    crud=crud,
                ),
            ]
        )
    return routes


def _build_crud_route(
    *,
    name: str,
    method: str,
    path: str,
    parameters: dict[str, ast.RouteField] | None,
    request: dict[str, ast.RouteField] | None,
    response: dict[str, ast.RouteField],
    flow_name: str,
    crud: ast.CrudDefinition,
) -> ast.RouteDefinition:
    return ast.RouteDefinition(
        name=name,
        path=path,
        method=method,
        parameters=parameters or {},
        request=request,
        response=response,
        flow_name=flow_name,
        upload=None,
        generated=True,
        line=crud.line,
        column=crud.column,
    )


def _crud_id_params(crud: ast.CrudDefinition) -> dict[str, ast.RouteField]:
    return {"id": _route_field("id", "number", crud)}


def _crud_request_fields(record_name: str, crud: ast.CrudDefinition) -> dict[str, ast.RouteField]:
    return {"body": _route_field("body", record_name, crud)}


def _crud_id_request_fields(crud: ast.CrudDefinition) -> dict[str, ast.RouteField]:
    return {"id": _route_field("id", "number", crud)}


def _crud_response_fields(
    record_slug: str,
    record_name: str,
    crud: ast.CrudDefinition,
) -> dict[str, ast.RouteField]:
    return {record_slug: _route_field(record_slug, record_name, crud)}


def _route_field(name: str, type_name: str, crud: ast.CrudDefinition) -> ast.RouteField:
    return ast.RouteField(
        name=name,
        type_name=type_name,
        type_was_alias=False,
        raw_type_name=None,
        type_line=crud.line,
        type_column=crud.column,
        line=crud.line,
        column=crud.column,
    )


def _record_slug(record_name: str) -> str:
    raw = str(record_name).split(".")[-1]
    return _camel_to_snake(raw)


def _camel_to_snake(value: str) -> str:
    return _CAMEL_BOUNDARY.sub(r"\1_\2", value).lower()


def _pluralize(value: str) -> str:
    return f"{value}s"


__all__ = ["expand_crud_routes"]

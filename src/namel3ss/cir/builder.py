from __future__ import annotations

from typing import Iterable

from namel3ss.ast import nodes as ast
from namel3ss.cir.model import CIRField, CIRFlow, CIRProgram, CIRRecord, CIRRoute


def build_cir(program: ast.Program) -> CIRProgram:
    records = tuple(
        _record_to_cir(record)
        for record in sorted(getattr(program, "records", []) or [], key=lambda item: item.name)
    )
    flows = tuple(
        _flow_to_cir(flow)
        for flow in sorted(getattr(program, "flows", []) or [], key=lambda item: item.name)
    )
    routes = tuple(
        _route_to_cir(route)
        for route in sorted(getattr(program, "routes", []) or [], key=lambda item: item.name)
    )
    return CIRProgram(
        spec_version=getattr(program, "spec_version", None),
        records=records,
        flows=flows,
        routes=routes,
    )


def _record_to_cir(record: ast.RecordDecl) -> CIRRecord:
    version = _record_version(record)
    fields = tuple(
        CIRField(name=field.name, type_name=field.type_name)
        for field in sorted(record.fields, key=lambda item: item.name)
    )
    return CIRRecord(name=record.name, version=version, fields=fields)


def _record_version(record: ast.RecordDecl) -> str | None:
    # Backward compatible: version metadata is optional and may not be present.
    version = getattr(record, "version", None)
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def _flow_to_cir(flow: ast.Flow) -> CIRFlow:
    statements = tuple(_statement_tag(stmt) for stmt in _flatten_statements(flow.body))
    return CIRFlow(name=flow.name, statements=statements)


def _route_to_cir(route: ast.RouteDefinition) -> CIRRoute:
    parameters = _sorted_route_fields(route.parameters or {})
    request = _sorted_route_fields(route.request or {})
    response = _sorted_route_fields(route.response or {})
    return CIRRoute(
        name=route.name,
        method=route.method,
        path=route.path,
        flow_name=route.flow_name,
        parameters=parameters,
        request=request,
        response=response,
    )


def _sorted_route_fields(fields: dict[str, ast.RouteField]) -> tuple[CIRField, ...]:
    return tuple(
        CIRField(name=name, type_name=field.type_name)
        for name, field in sorted(fields.items(), key=lambda item: item[0])
    )


def _flatten_statements(statements: Iterable[ast.Statement]) -> tuple[ast.Statement, ...]:
    values: list[ast.Statement] = []
    for stmt in statements:
        values.append(stmt)
    return tuple(values)


def _statement_tag(stmt: ast.Statement) -> str:
    return stmt.__class__.__name__


__all__ = ["build_cir"]

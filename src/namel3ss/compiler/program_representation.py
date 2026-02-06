from __future__ import annotations

from dataclasses import asdict, dataclass

from namel3ss import ast
from namel3ss.cir import build_cir
from namel3ss.cir.model import CIRField, CIRFlow, CIRProgram, CIRRecord, CIRRoute
from namel3ss.determinism import canonical_json_dumps


PROGRAM_REPRESENTATION_SCHEMA = "program_representation.v1"


@dataclass(frozen=True)
class ProgramField:
    name: str
    type_name: str


@dataclass(frozen=True)
class ProgramRecord:
    name: str
    version: str | None
    fields: tuple[ProgramField, ...]


@dataclass(frozen=True)
class ProgramFlow:
    name: str
    statements: tuple[str, ...]


@dataclass(frozen=True)
class ProgramRoute:
    name: str
    method: str
    path: str
    flow_name: str
    parameters: tuple[ProgramField, ...]
    request: tuple[ProgramField, ...]
    response: tuple[ProgramField, ...]


@dataclass(frozen=True)
class ProgramRepresentation:
    spec_version: str | None
    records: tuple[ProgramRecord, ...]
    flows: tuple[ProgramFlow, ...]
    routes: tuple[ProgramRoute, ...]


def build_program_representation(program_ast: ast.Program) -> ProgramRepresentation:
    cir = build_cir(program_ast)
    return _representation_from_cir(cir)


def program_representation_to_payload(representation: ProgramRepresentation) -> dict[str, object]:
    return asdict(representation)


def program_representation_to_json(representation: ProgramRepresentation, *, pretty: bool = True) -> str:
    payload = program_representation_to_payload(representation)
    return canonical_json_dumps(payload, pretty=pretty, drop_run_keys=False)


def _representation_from_cir(cir: CIRProgram) -> ProgramRepresentation:
    return ProgramRepresentation(
        spec_version=cir.spec_version,
        records=tuple(_record_from_cir(item) for item in cir.records),
        flows=tuple(_flow_from_cir(item) for item in cir.flows),
        routes=tuple(_route_from_cir(item) for item in cir.routes),
    )


def _field_from_cir(field: CIRField) -> ProgramField:
    return ProgramField(name=field.name, type_name=field.type_name)


def _record_from_cir(record: CIRRecord) -> ProgramRecord:
    return ProgramRecord(
        name=record.name,
        version=record.version,
        fields=tuple(_field_from_cir(item) for item in record.fields),
    )


def _flow_from_cir(flow: CIRFlow) -> ProgramFlow:
    return ProgramFlow(
        name=flow.name,
        statements=tuple(flow.statements),
    )


def _route_from_cir(route: CIRRoute) -> ProgramRoute:
    return ProgramRoute(
        name=route.name,
        method=route.method,
        path=route.path,
        flow_name=route.flow_name,
        parameters=tuple(_field_from_cir(item) for item in route.parameters),
        request=tuple(_field_from_cir(item) for item in route.request),
        response=tuple(_field_from_cir(item) for item in route.response),
    )


__all__ = [
    "PROGRAM_REPRESENTATION_SCHEMA",
    "ProgramField",
    "ProgramFlow",
    "ProgramRecord",
    "ProgramRepresentation",
    "ProgramRoute",
    "build_program_representation",
    "program_representation_to_json",
    "program_representation_to_payload",
]

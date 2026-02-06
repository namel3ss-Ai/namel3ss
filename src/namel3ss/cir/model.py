from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CIRField:
    name: str
    type_name: str


@dataclass(frozen=True)
class CIRRecord:
    name: str
    version: str | None
    fields: tuple[CIRField, ...]


@dataclass(frozen=True)
class CIRFlow:
    name: str
    statements: tuple[str, ...]


@dataclass(frozen=True)
class CIRRoute:
    name: str
    method: str
    path: str
    flow_name: str
    parameters: tuple[CIRField, ...]
    request: tuple[CIRField, ...]
    response: tuple[CIRField, ...]


@dataclass(frozen=True)
class CIRProgram:
    spec_version: str | None
    records: tuple[CIRRecord, ...]
    flows: tuple[CIRFlow, ...]
    routes: tuple[CIRRoute, ...]


__all__ = [
    "CIRField",
    "CIRFlow",
    "CIRProgram",
    "CIRRecord",
    "CIRRoute",
]

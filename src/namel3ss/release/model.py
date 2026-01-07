from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateSpec:
    name: str
    tests: tuple[str, ...]
    required: bool = True
    command: tuple[str, ...] | None = None


@dataclass(frozen=True)
class GateResult:
    name: str
    required: bool
    status: str
    code: str
    summary: str
    details: dict

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "required": self.required,
            "status": self.status,
            "code": self.code,
            "summary": self.summary,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ReleaseReport:
    schema_version: str
    namel3ss_version: str
    environment: dict
    gates: tuple[GateResult, ...]
    summary: dict

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "namel3ss_version": self.namel3ss_version,
            "environment": dict(self.environment),
            "gates": [gate.as_dict() for gate in self.gates],
            "summary": dict(self.summary),
        }


__all__ = ["GateSpec", "GateResult", "ReleaseReport"]

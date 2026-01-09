from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


EVAL_SCHEMA_VERSION = "evals.v1"


@dataclass(frozen=True)
class ToolCallSpec:
    tool_name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class MockProviderSpec:
    tool_calls: tuple[ToolCallSpec, ...]
    response: str | None


@dataclass(frozen=True)
class EvalExpectations:
    ok: bool
    result: Any | None
    error_contains: str | None
    tool_calls: tuple[str, ...] | None
    tool_blocks: tuple[str, ...] | None
    trace_hash: str | None


@dataclass(frozen=True)
class EvalMemoryPacks:
    default_pack: str | None
    agent_overrides: dict[str, str]


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    app: str
    flow: str
    input: dict[str, Any]
    state: dict[str, Any]
    identity: dict[str, Any] | None
    expect: EvalExpectations
    tags: tuple[str, ...]
    mock: MockProviderSpec | None
    tool_bindings: dict[str, dict[str, Any]] | None
    memory_packs: EvalMemoryPacks | None


@dataclass(frozen=True)
class EvalThresholds:
    success_rate: float | None
    tool_accuracy: float | None
    max_policy_violations: int | None


@dataclass(frozen=True)
class EvalSuite:
    schema_version: str
    cases: tuple[EvalCase, ...]
    thresholds: EvalThresholds
    path: Path


@dataclass(frozen=True)
class EvalCaseResult:
    case_id: str
    app: str
    flow: str
    status: str
    duration_ms: int
    ai_calls: int
    result_hash: str | None
    trace_hash: str | None
    tool_calls: tuple[str, ...]
    tool_blocks: tuple[str, ...]
    policy_violations: int
    error: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.case_id,
            "app": self.app,
            "flow": self.flow,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "ai_calls": self.ai_calls,
            "result_hash": self.result_hash,
            "trace_hash": self.trace_hash,
            "tool_calls": list(self.tool_calls),
            "tool_blocks": list(self.tool_blocks),
            "policy_violations": self.policy_violations,
        }
        if self.error:
            payload["error"] = dict(self.error)
        return payload


@dataclass(frozen=True)
class EvalReport:
    schema_version: str
    namel3ss_version: str
    status: str
    summary: dict[str, Any]
    thresholds: list[dict[str, Any]]
    cases: tuple[EvalCaseResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "namel3ss_version": self.namel3ss_version,
            "status": self.status,
            "summary": dict(self.summary),
            "thresholds": list(self.thresholds),
            "cases": [case.as_dict() for case in self.cases],
        }


__all__ = [
    "EVAL_SCHEMA_VERSION",
    "EvalCase",
    "EvalCaseResult",
    "EvalExpectations",
    "EvalMemoryPacks",
    "EvalReport",
    "EvalSuite",
    "EvalThresholds",
    "MockProviderSpec",
    "ToolCallSpec",
]

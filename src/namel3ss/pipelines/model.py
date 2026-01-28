from __future__ import annotations

from dataclasses import dataclass
import hashlib

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class StepField:
    name: str
    type_name: str
    required: bool = True


@dataclass(frozen=True)
class PipelineStep:
    kind: str
    summary_fields: tuple[StepField, ...]
    description: str | None = None


@dataclass(frozen=True)
class PipelineDefinition:
    name: str
    purity: str
    steps: tuple[PipelineStep, ...]


@dataclass(frozen=True)
class PipelineStepResult:
    step_id: str
    kind: str
    status: str
    summary: dict
    checksum: str
    ordinal: int


@dataclass(frozen=True)
class PipelineRunResult:
    output: dict
    steps: list[PipelineStepResult]
    status: str


def pipeline_step_id(pipeline_name: str, step_kind: str, ordinal: int) -> str:
    return f"pipeline:{pipeline_name}:{step_kind}:{ordinal:02d}"


def step_checksum(summary: dict) -> str:
    payload = canonical_json_dumps(summary, pretty=False, drop_run_keys=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_step_summary(step: PipelineStep, summary: dict) -> None:
    if not isinstance(summary, dict):
        raise Namel3ssError(f"Pipeline step summary for '{step.kind}' must be a map.")
    for field in step.summary_fields:
        if field.name not in summary:
            if field.required:
                raise Namel3ssError(f"Pipeline step '{step.kind}' is missing '{field.name}'.")
            continue
        value = summary.get(field.name)
        if not _is_type(value, field.type_name):
            raise Namel3ssError(
                f"Pipeline step '{step.kind}' field '{field.name}' must be {field.type_name}."
            )


def _is_type(value: object, type_name: str) -> bool:
    if type_name == "text":
        return isinstance(value, str)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "map":
        return isinstance(value, dict)
    if type_name == "json":
        return isinstance(value, (str, int, float, bool, dict, list)) or value is None
    return False


__all__ = [
    "PipelineDefinition",
    "PipelineRunResult",
    "PipelineStep",
    "PipelineStepResult",
    "StepField",
    "pipeline_step_id",
    "step_checksum",
    "validate_step_summary",
]

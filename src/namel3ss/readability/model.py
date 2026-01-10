from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlumbingCounts:
    find: int
    delete: int
    create: int
    update: int
    save: int
    set_state: int
    try_catch: int
    list_get: int
    list_length: int
    map_get: int
    index_patterns: int
    statement_ops: int
    structure_ops: int
    total: int


@dataclass(frozen=True)
class IntentCounts:
    ask_ai: int
    run_agent: int
    run_parallel: int
    comparisons: int
    ui_button_calls: int
    record_constraints_must: int
    total: int


@dataclass(frozen=True)
class ComplexityCounts:
    branches: int
    max_depth: int
    record_refs: int
    distinct_state_writes: int


@dataclass(frozen=True)
class ScoreInputs:
    plumbing_weighted: int
    structure_ops: int
    branches: int
    indent_depth: int


@dataclass(frozen=True)
class Scorecard:
    score: int
    plumbing_ratio: float
    plumbing_weighted: int
    structure_ops: int
    branches: int
    indent_depth: int
    score_inputs: ScoreInputs


@dataclass(frozen=True)
class OffenderCount:
    name: str
    count: int


@dataclass(frozen=True)
class FlowReport:
    name: str
    statement_count: int
    plumbing_ratio: float
    plumbing: PlumbingCounts
    intent: IntentCounts
    complexity: ComplexityCounts
    scorecard: Scorecard
    top_offenders: list[OffenderCount]


@dataclass(frozen=True)
class UIFlowBinding:
    flow: str
    count: int


@dataclass(frozen=True)
class FileReport:
    path: str
    flow_count: int
    record_constraints_must: int
    ui_button_bindings_total: int
    ui_button_bindings: list[UIFlowBinding]
    flows: list[FlowReport]
    top_offenders: list[OffenderCount]


@dataclass(frozen=True)
class ReadabilityReport:
    schema_version: int
    analyzed_path: str
    score_formula: str
    score_weights: dict[str, int]
    file_count: int
    flow_count: int
    files: list[FileReport]


__all__ = [
    "ComplexityCounts",
    "FileReport",
    "FlowReport",
    "IntentCounts",
    "OffenderCount",
    "PlumbingCounts",
    "ReadabilityReport",
    "Scorecard",
    "ScoreInputs",
    "UIFlowBinding",
]

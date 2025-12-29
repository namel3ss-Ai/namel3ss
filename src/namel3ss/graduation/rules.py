from __future__ import annotations

from dataclasses import dataclass

from namel3ss.graduation.capabilities import STATUS_SHIPPED


AI_LANGUAGE_REQUIRED = (
    "language.core",
    "compute.core",
    "compute.collections",
    "runtime.tools",
    "runtime.ai",
    "runtime.memory",
    "runtime.modules",
    "runtime.concurrency",
    "runtime.traces",
)

BETA_REQUIRED = (
    *AI_LANGUAGE_REQUIRED,
    "runtime.memory_packs",
    "runtime.provider_coverage",
)

STABILITY_PROMISES = (
    "Parser and IR outputs are locked by golden tests",
    "Trace contracts are locked by golden tests",
    "Runtime output is deterministic for identical inputs",
    "Line limit checks enforce small files",
)

STABILITY_CHECKS = (
    "tests/spec_freeze/test_parser_golden.py",
    "tests/spec_freeze/test_ir_golden.py",
    "tests/spec_freeze/test_trace_contracts.py",
    "tools/line_limit_check.py",
)


@dataclass(frozen=True)
class GraduationReport:
    ai_language_ready: bool
    beta_ready: bool
    missing_ai_language: tuple[str, ...]
    missing_beta: tuple[str, ...]


def evaluate_graduation(matrix: dict) -> GraduationReport:
    status_by_id = _status_map(matrix)
    missing_ai = tuple(
        cap_id for cap_id in AI_LANGUAGE_REQUIRED if status_by_id.get(cap_id) != STATUS_SHIPPED
    )
    missing_beta = tuple(
        cap_id for cap_id in BETA_REQUIRED if status_by_id.get(cap_id) != STATUS_SHIPPED
    )
    return GraduationReport(
        ai_language_ready=not missing_ai,
        beta_ready=not missing_beta,
        missing_ai_language=missing_ai,
        missing_beta=missing_beta,
    )


def _status_map(matrix: dict) -> dict[str, str]:
    status_by_id: dict[str, str] = {}
    for item in matrix.get("capabilities") or []:
        cap_id = str(item.get("id") or "")
        status = str(item.get("status") or "")
        status_by_id[cap_id] = status
    return status_by_id


__all__ = [
    "AI_LANGUAGE_REQUIRED",
    "BETA_REQUIRED",
    "GraduationReport",
    "STABILITY_CHECKS",
    "STABILITY_PROMISES",
    "evaluate_graduation",
]

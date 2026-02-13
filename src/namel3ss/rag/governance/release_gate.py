from __future__ import annotations

from namel3ss.rag.contracts.value_norms import (
    float_value,
    int_value,
    map_value,
    merge_extensions,
    sorted_string_list,
    text_value,
)
from namel3ss.rag.deployment.deployment_profile import (
    build_load_soak_result,
    evaluate_load_soak_result,
    normalize_deployment_profile,
    normalize_load_soak_assessment,
    normalize_load_soak_result,
    normalize_service_slo_model,
)
from namel3ss.rag.determinism.json_policy import canonical_contract_copy, canonical_contract_hash
from namel3ss.rag.evaluation.regression_report import normalize_regression_report, regression_gate_passed
from namel3ss.rag.migrations.migration_runner import normalize_migration_report


RUNBOOK_STATUS_SCHEMA_VERSION = "rag.runbook_status@1"
RELEASE_READINESS_SCHEMA_VERSION = "rag.release_readiness@1"


def build_runbook_status(
    *,
    path: str,
    required_sections: object,
    present_sections: object,
    complete: bool | None = None,
    schema_version: str = RUNBOOK_STATUS_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    required_rows = sorted_string_list(required_sections)
    present_rows = sorted_string_list(present_sections)
    missing_rows = [section for section in required_rows if section not in set(present_rows)]
    complete_value = bool(complete) if isinstance(complete, bool) else len(missing_rows) == 0
    fingerprint = canonical_contract_hash(
        {
            "path": text_value(path),
            "present_sections": present_rows,
            "required_sections": required_rows,
        }
    )
    return {
        "schema_version": text_value(schema_version, default=RUNBOOK_STATUS_SCHEMA_VERSION) or RUNBOOK_STATUS_SCHEMA_VERSION,
        "path": text_value(path),
        "required_sections": required_rows,
        "present_sections": present_rows,
        "missing_sections": missing_rows,
        "complete": complete_value and len(missing_rows) == 0,
        "runbook_fingerprint": f"runbook_{fingerprint[:20]}",
        "extensions": merge_extensions(extensions),
    }


def normalize_runbook_status(value: object) -> dict[str, object]:
    data = map_value(value)
    return build_runbook_status(
        path=text_value(data.get("path")),
        required_sections=data.get("required_sections"),
        present_sections=data.get("present_sections"),
        complete=bool(data.get("complete")) if isinstance(data.get("complete"), bool) else None,
        schema_version=text_value(data.get("schema_version"), default=RUNBOOK_STATUS_SCHEMA_VERSION)
        or RUNBOOK_STATUS_SCHEMA_VERSION,
        extensions=data.get("extensions"),
    )


def build_release_readiness_report(
    *,
    deployment_profile: object,
    migration_report: object,
    regression_report: object,
    load_soak_result: object | None = None,
    runbook_status: object | None = None,
    schema_version: str = RELEASE_READINESS_SCHEMA_VERSION,
    extensions: dict[str, object] | None = None,
) -> dict[str, object]:
    profile = normalize_deployment_profile(deployment_profile)
    migration = normalize_migration_report(migration_report)
    regression = normalize_regression_report(regression_report)
    load_soak = normalize_load_soak_result(load_soak_result) if load_soak_result is not None else build_load_soak_result()
    assessment = evaluate_load_soak_result(deployment_profile=profile, load_soak_result=load_soak)
    runbook = normalize_runbook_status(runbook_status or _default_runbook_status())
    gates = _build_gates(
        deployment_profile=profile,
        migration_report=migration,
        regression_report=regression,
        load_soak_assessment=assessment,
        runbook_status=runbook,
    )
    gates.sort(key=lambda row: text_value(row.get("gate_id")))
    summary = _build_summary(gates)
    passed = summary["required_failed"] == 0
    return {
        "schema_version": text_value(schema_version, default=RELEASE_READINESS_SCHEMA_VERSION)
        or RELEASE_READINESS_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "summary": summary,
        "gates": gates,
        "deployment_profile": canonical_contract_copy(profile),
        "migration_report": canonical_contract_copy(migration),
        "regression_report": canonical_contract_copy(regression),
        "load_soak_assessment": canonical_contract_copy(assessment),
        "runbook_status": canonical_contract_copy(runbook),
        "extensions": merge_extensions(extensions),
    }


def normalize_release_readiness_report(value: object) -> dict[str, object]:
    data = map_value(value)
    gates = _normalize_gate_rows(data.get("gates"))
    summary = _normalize_summary(data.get("summary"), gates=gates)
    passed = summary["required_failed"] == 0
    return {
        "schema_version": text_value(data.get("schema_version"), default=RELEASE_READINESS_SCHEMA_VERSION)
        or RELEASE_READINESS_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "summary": summary,
        "gates": gates,
        "deployment_profile": normalize_deployment_profile(data.get("deployment_profile")),
        "migration_report": normalize_migration_report(data.get("migration_report")),
        "regression_report": normalize_regression_report(data.get("regression_report")),
        "load_soak_assessment": normalize_load_soak_assessment(data.get("load_soak_assessment")),
        "runbook_status": normalize_runbook_status(data.get("runbook_status")),
        "extensions": merge_extensions(data.get("extensions")),
    }


def release_ready(report: object) -> bool:
    normalized = normalize_release_readiness_report(report)
    return bool(normalized.get("passed"))


def raise_on_release_blockers(report: object) -> None:
    normalized = normalize_release_readiness_report(report)
    if bool(normalized.get("passed")):
        return
    blockers = [
        text_value(gate.get("gate_id"))
        for gate in normalized.get("gates") or []
        if bool(gate.get("required")) and not bool(gate.get("passed"))
    ]
    blocker_text = ", ".join(blockers)
    message = "RAG release readiness check failed"
    if blocker_text:
        message = f"{message}: {blocker_text}"
    raise RuntimeError(message)


def _build_gates(
    *,
    deployment_profile: dict[str, object],
    migration_report: dict[str, object],
    regression_report: dict[str, object],
    load_soak_assessment: dict[str, object],
    runbook_status: dict[str, object],
) -> list[dict[str, object]]:
    return [
        _deployment_profile_gate(deployment_profile),
        _service_slo_gate(deployment_profile.get("service_slo")),
        _migration_gate(migration_report),
        _regression_gate(regression_report),
        _load_soak_gate(load_soak_assessment),
        _runbook_gate(runbook_status),
    ]


def _deployment_profile_gate(profile: dict[str, object]) -> dict[str, object]:
    environment = text_value(profile.get("environment"), default="production") or "production"
    replicas = int_value(profile.get("replicas"), default=0, minimum=0)
    stream_transport = text_value(profile.get("stream_transport"), default="sse") or "sse"
    minimum_replicas = 2 if environment == "production" else 1
    passed = replicas >= minimum_replicas and stream_transport == "sse"
    return _gate_row(
        gate_id="deployment.profile_valid",
        passed=passed,
        required=True,
        summary="profile settings satisfy runtime minimums",
        details={
            "environment": environment,
            "minimum_replicas": minimum_replicas,
            "replicas": replicas,
            "stream_transport": stream_transport,
        },
    )


def _service_slo_gate(value: object) -> dict[str, object]:
    slo = normalize_service_slo_model(value)
    availability_target = float(slo.get("availability_target") or 0.0)
    max_error_rate = float(slo.get("max_error_rate") or 1.0)
    p95 = int_value(slo.get("p95_latency_ms"), default=0, minimum=0)
    p99 = int_value(slo.get("p99_latency_ms"), default=0, minimum=0)
    grounding = float(slo.get("min_citation_grounding") or 0.0)
    passed = (
        availability_target >= 0.95
        and max_error_rate <= 0.1
        and p95 > 0
        and p99 >= p95
        and grounding >= 0.9
    )
    return _gate_row(
        gate_id="deployment.service_slo_valid",
        passed=passed,
        required=True,
        summary="service SLO contract has production-safe bounds",
        details={
            "availability_target": availability_target,
            "max_error_rate": max_error_rate,
            "min_citation_grounding": grounding,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
        },
    )


def _migration_gate(report: dict[str, object]) -> dict[str, object]:
    status = text_value(report.get("status"))
    replay_safe = bool(report.get("replay_safe"))
    failed_steps = int_value(map_value(report.get("summary")).get("failed_steps"), default=0, minimum=0)
    passed = replay_safe and failed_steps == 0 and status in {"applied", "noop", "already_applied"}
    return _gate_row(
        gate_id="migrations.replay_safe",
        passed=passed,
        required=True,
        summary="migration manifest remains replay-safe and idempotent",
        details={
            "failed_steps": failed_steps,
            "manifest_id": text_value(report.get("manifest_id")),
            "replay_safe": replay_safe,
            "status": status,
        },
    )


def _regression_gate(report: dict[str, object]) -> dict[str, object]:
    passed = regression_gate_passed(report)
    return _gate_row(
        gate_id="evaluation.regression_pass",
        passed=passed,
        required=True,
        summary="eval regression gates are green",
        details={
            "baseline_run_fingerprint": text_value(report.get("baseline_run_fingerprint")),
            "current_run_fingerprint": text_value(report.get("current_run_fingerprint")),
            "status": text_value(report.get("status")),
        },
    )


def _load_soak_gate(value: object) -> dict[str, object]:
    assessment = normalize_load_soak_assessment(value)
    passed = bool(assessment.get("passed"))
    return _gate_row(
        gate_id="runtime.load_soak_pass",
        passed=passed,
        required=True,
        summary="load and soak checks satisfy SLO thresholds",
        details={
            "check_count": len(list(assessment.get("checks") or [])),
            "profile_environment": text_value(assessment.get("profile_environment")),
            "status": text_value(assessment.get("status")),
        },
    )


def _runbook_gate(value: object) -> dict[str, object]:
    runbook = normalize_runbook_status(value)
    passed = bool(runbook.get("complete")) and bool(text_value(runbook.get("path")))
    return _gate_row(
        gate_id="docs.runbook_complete",
        passed=passed,
        required=True,
        summary="operations runbook exists and includes required sections",
        details={
            "missing_sections": list(runbook.get("missing_sections") or []),
            "path": text_value(runbook.get("path")),
            "runbook_fingerprint": text_value(runbook.get("runbook_fingerprint")),
        },
    )


def _default_runbook_status() -> dict[str, object]:
    return build_runbook_status(
        path="",
        required_sections=_REQUIRED_RUNBOOK_SECTIONS,
        present_sections=[],
        complete=False,
    )


def _gate_row(
    *,
    gate_id: str,
    passed: bool,
    required: bool,
    summary: str,
    details: object,
) -> dict[str, object]:
    return {
        "gate_id": text_value(gate_id),
        "passed": bool(passed),
        "required": bool(required),
        "severity": "blocker" if required else "warning",
        "summary": text_value(summary),
        "details": canonical_contract_copy(details),
    }


def _normalize_gate_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        data = map_value(item)
        rows.append(
            {
                "gate_id": text_value(data.get("gate_id")),
                "passed": bool(data.get("passed")),
                "required": bool(data.get("required")),
                "severity": text_value(data.get("severity"), default="blocker") or "blocker",
                "summary": text_value(data.get("summary")),
                "details": canonical_contract_copy(data.get("details")),
            }
        )
    rows.sort(key=lambda row: text_value(row.get("gate_id")))
    return rows


def _build_summary(gates: list[dict[str, object]]) -> dict[str, int]:
    required_total = sum(1 for gate in gates if bool(gate.get("required")))
    required_passed = sum(1 for gate in gates if bool(gate.get("required")) and bool(gate.get("passed")))
    required_failed = required_total - required_passed
    optional_total = len(gates) - required_total
    optional_failed = sum(1 for gate in gates if not bool(gate.get("required")) and not bool(gate.get("passed")))
    return {
        "optional_failed": optional_failed,
        "optional_total": optional_total,
        "required_failed": required_failed,
        "required_passed": required_passed,
        "required_total": required_total,
    }


def _normalize_summary(value: object, *, gates: list[dict[str, object]]) -> dict[str, int]:
    data = map_value(value)
    fallback = _build_summary(gates)
    return {
        "optional_failed": int_value(data.get("optional_failed"), default=fallback["optional_failed"], minimum=0),
        "optional_total": int_value(data.get("optional_total"), default=fallback["optional_total"], minimum=0),
        "required_failed": int_value(data.get("required_failed"), default=fallback["required_failed"], minimum=0),
        "required_passed": int_value(data.get("required_passed"), default=fallback["required_passed"], minimum=0),
        "required_total": int_value(data.get("required_total"), default=fallback["required_total"], minimum=0),
    }


_REQUIRED_RUNBOOK_SECTIONS = [
    "preflight",
    "deployment",
    "migration_replay",
    "load_soak",
    "release_gate",
    "rollback",
]


__all__ = [
    "RELEASE_READINESS_SCHEMA_VERSION",
    "RUNBOOK_STATUS_SCHEMA_VERSION",
    "build_release_readiness_report",
    "build_runbook_status",
    "normalize_release_readiness_report",
    "normalize_runbook_status",
    "raise_on_release_blockers",
    "release_ready",
]

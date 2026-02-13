from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from namel3ss.rag.deployment import (
    build_deployment_profile,
    build_load_soak_result,
    evaluate_load_soak_result,
    normalize_deployment_profile,
)
from namel3ss.rag.governance import (
    build_release_readiness_report,
    build_runbook_status,
    raise_on_release_blockers,
    release_ready,
)
from namel3ss.rag.migrations import (
    build_migration_manifest,
    build_migration_step,
    run_migration_manifest,
)


def test_phase6_migration_manifest_is_replay_safe_and_idempotent() -> None:
    state: dict = {"rag": {"legacy": {"enabled": True}}}
    manifest = build_migration_manifest(
        name="rag-runtime-foundation",
        steps=[
            build_migration_step(
                operation="rename_value",
                from_path="rag.legacy.enabled",
                target_path="rag.runtime.enabled",
            ),
            build_migration_step(
                operation="set_value",
                target_path="rag.runtime.schema_version",
                value="rag.runtime@1",
            ),
            build_migration_step(
                operation="remove_value",
                target_path="rag.legacy",
            ),
        ],
    )

    first = run_migration_manifest(state=state, manifest=manifest)
    second = run_migration_manifest(state=state, manifest=manifest)

    assert first["status"] == "applied"
    assert first["replay_safe"] is True
    assert second["status"] == "already_applied"
    assert second["replay_safe"] is True
    assert first["state_hash_after"] == second["state_hash_before"]
    assert state["rag"]["runtime"]["enabled"] is True
    assert state["rag"]["runtime"]["schema_version"] == "rag.runtime@1"
    assert "legacy" not in state["rag"]


def test_phase6_migration_dry_run_does_not_mutate_state() -> None:
    state: dict = {"rag": {"settings": {"mode": "legacy"}}}
    before = deepcopy(state)
    manifest = build_migration_manifest(
        name="dry-run-check",
        steps=[
            build_migration_step(
                operation="set_value",
                target_path="rag.settings.mode",
                value="stable",
            )
        ],
    )

    report = run_migration_manifest(state=state, manifest=manifest, dry_run=True)

    assert report["dry_run"] is True
    assert report["status"] == "applied"
    assert report["replay_safe"] is True
    assert state == before


def test_phase6_deployment_and_load_soak_assessment_are_deterministic() -> None:
    first_profile = normalize_deployment_profile(
        {
            "feature_flags": ["rag_trace", "rag_preview", "rag_trace"],
            "service_slo": {
                "availability_target": 0.999,
                "p99_latency_ms": 1600,
                "p95_latency_ms": 900,
                "max_error_rate": 0.01,
                "max_retrieval_drift": 0.0,
                "min_citation_grounding": 0.99,
            },
            "load_targets": {
                "min_soak_minutes": 15,
                "target_concurrency": 20,
                "min_requests_total": 200,
            },
        }
    )
    second_profile = normalize_deployment_profile(
        {
            "service_slo": {
                "p95_latency_ms": 900,
                "availability_target": 0.999,
                "max_retrieval_drift": 0.0,
                "max_error_rate": 0.01,
                "min_citation_grounding": 0.99,
                "p99_latency_ms": 1600,
            },
            "feature_flags": ["rag_preview", "rag_trace"],
            "load_targets": {
                "target_concurrency": 20,
                "min_requests_total": 200,
                "min_soak_minutes": 15,
            },
        }
    )
    result = build_load_soak_result(
        run_label="baseline",
        requests_total=400,
        requests_failed=2,
        latency_p95_ms=850,
        latency_p99_ms=1400,
        soak_minutes=25,
        retrieval_drift=0.0,
        citation_grounding=1.0,
    )

    first_assessment = evaluate_load_soak_result(
        deployment_profile=first_profile,
        load_soak_result=result,
    )
    second_assessment = evaluate_load_soak_result(
        deployment_profile=second_profile,
        load_soak_result=result,
    )

    assert first_profile == second_profile
    assert first_assessment == second_assessment
    assert first_assessment["passed"] is True


def test_phase6_load_and_soak_gate_fails_on_slo_breach() -> None:
    profile = build_deployment_profile()
    bad_result = build_load_soak_result(
        run_label="degraded",
        requests_total=40,
        requests_failed=15,
        latency_p95_ms=4500,
        latency_p99_ms=7000,
        soak_minutes=1,
        retrieval_drift=0.35,
        citation_grounding=0.5,
    )

    assessment = evaluate_load_soak_result(
        deployment_profile=profile,
        load_soak_result=bad_result,
    )

    assert assessment["passed"] is False
    failed_checks = [row["check_id"] for row in assessment["checks"] if not row["passed"]]
    assert "availability_target" in failed_checks
    assert "latency_p95_ms" in failed_checks
    assert "latency_p99_ms" in failed_checks
    assert "retrieval_drift" in failed_checks


def test_phase6_release_gate_validates_checklist_and_blocks_failures() -> None:
    profile = build_deployment_profile(
        service_slo={
            "availability_target": 0.999,
            "max_error_rate": 0.01,
            "p95_latency_ms": 900,
            "p99_latency_ms": 1600,
            "max_retrieval_drift": 0.0,
            "min_citation_grounding": 0.99,
        },
        load_targets={
            "min_requests_total": 150,
            "min_soak_minutes": 10,
            "target_concurrency": 10,
        },
    )
    state: dict = {}
    migration_manifest = build_migration_manifest(
        name="phase6-release-check",
        steps=[
            build_migration_step(
                operation="set_value",
                target_path="rag.runtime.schema_version",
                value="rag.runtime@1",
            )
        ],
    )
    migration_report = run_migration_manifest(state=state, manifest=migration_manifest)
    load_soak_result = build_load_soak_result(
        run_label="release-candidate",
        requests_total=500,
        requests_failed=2,
        latency_p95_ms=700,
        latency_p99_ms=1200,
        soak_minutes=30,
        retrieval_drift=0.0,
        citation_grounding=1.0,
    )
    runbook_status = build_runbook_status(
        path="docs/rag_v1_operations_runbook.md",
        required_sections=[
            "preflight",
            "deployment",
            "migration_replay",
            "load_soak",
            "release_gate",
            "rollback",
        ],
        present_sections=[
            "rollback",
            "release_gate",
            "deployment",
            "preflight",
            "migration_replay",
            "load_soak",
        ],
    )
    regression_pass = {
        "schema_version": "rag.eval_regression@1",
        "status": "pass",
        "passed": True,
        "gates": [{"gate_id": "eval.pass", "operator": "gte", "actual": 1.0, "required": 1.0, "passed": True}],
        "current_summary": {"pass_rate": 1.0, "avg_overall_score": 1.0, "avg_citation_grounding": 1.0},
        "baseline_summary": {"pass_rate": 1.0, "avg_overall_score": 1.0, "avg_citation_grounding": 1.0},
        "thresholds": {},
    }

    report = build_release_readiness_report(
        deployment_profile=profile,
        migration_report=migration_report,
        regression_report=regression_pass,
        load_soak_result=load_soak_result,
        runbook_status=runbook_status,
    )

    assert release_ready(report) is True
    gate_ids = [gate["gate_id"] for gate in report["gates"]]
    assert gate_ids == sorted(gate_ids)
    assert gate_ids == [
        "deployment.profile_valid",
        "deployment.service_slo_valid",
        "docs.runbook_complete",
        "evaluation.regression_pass",
        "migrations.replay_safe",
        "runtime.load_soak_pass",
    ]

    regression_fail = deepcopy(regression_pass)
    regression_fail["passed"] = False
    regression_fail["status"] = "fail"
    regression_fail["gates"] = [
        {"gate_id": "eval.pass", "operator": "gte", "actual": 0.4, "required": 1.0, "passed": False}
    ]
    failed_report = build_release_readiness_report(
        deployment_profile=profile,
        migration_report=migration_report,
        regression_report=regression_fail,
        load_soak_result=load_soak_result,
        runbook_status=runbook_status,
    )
    assert release_ready(failed_report) is False
    with pytest.raises(RuntimeError):
        raise_on_release_blockers(failed_report)


def test_phase6_operations_runbook_has_required_sections() -> None:
    runbook = Path("docs/rag_v1_operations_runbook.md")
    text = runbook.read_text(encoding="utf-8")

    assert "## Preflight" in text
    assert "## Deployment" in text
    assert "## Migration Replay" in text
    assert "## Load And Soak" in text
    assert "## Release Gate" in text
    assert "## Rollback" in text


__all__ = []

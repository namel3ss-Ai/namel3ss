from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow

FIXTURE = Path("tests/fixtures/orchestration_policies.ai")
NO_ORCH_FIXTURE = Path("tests/fixtures/flow_purity_no_declaration.ai")


def _source() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_orchestration_branch_order() -> None:
    result = run_flow(_source(), flow_name="all_ok_flow")
    assert [item["result"] for item in result.last_value] == ["beta", "alpha"]


def test_orchestration_first_ok() -> None:
    result = run_flow(_source(), flow_name="first_ok_flow")
    assert result.last_value == "alpha"


def test_orchestration_prefer_policy() -> None:
    result = run_flow(_source(), flow_name="prefer_flow")
    assert result.last_value == "beta"


def test_orchestration_collect_policy() -> None:
    result = run_flow(_source(), flow_name="collect_flow")
    assert result.last_value[0]["branch"] == "fail"
    assert result.last_value[0]["status"] == "error"
    assert result.last_value[1]["branch"] == "beta"
    assert result.last_value[1]["status"] == "ok"


def test_orchestration_deterministic() -> None:
    first = run_flow(_source(), flow_name="first_ok_flow")
    second = run_flow(_source(), flow_name="first_ok_flow")
    assert first.last_value == second.last_value
    assert first.traces == second.traces


def test_orchestration_trace_has_policy_and_decision() -> None:
    result = run_flow(_source(), flow_name="first_ok_flow")
    events = [event for event in result.traces if isinstance(event, dict)]
    merge_events = [event for event in events if event.get("type") == "orchestration_merge_finished"]
    assert len(merge_events) == 1
    event = merge_events[0]
    assert event["policy"] == "first_ok"
    assert event.get("decision")
    assert event["decision"].get("reason")


def test_orchestration_strict_failure() -> None:
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(_source(), flow_name="strict_flow")
    assert str(excinfo.value) == (
        "[line 114, col 3] error: Runtime error.\n\n"
        "What happened\n"
        "- Runtime error.\n\n"
        "Why\n"
        "- Error message: Orchestration merge failed: strict requires all branches to succeed. Failed branches: fail.\n"
        "- The engine raised an error.\n\n"
        "How to fix\n"
        "- Review the error message and try again.\n\n"
        "Where\n"
        "- flow: strict_flow\n"
        "- statement: orchestration\n"
        "- statement index: 1\n"
        "- line: 114\n"
        "- column: 3\n\n"
        "Error id\n"
        "- E-ENGINE-ENGINE_ERROR-STRICT_FLOW-ORCHESTRATION-1"
    )


def test_non_orchestrated_flow_unchanged() -> None:
    source = NO_ORCH_FIXTURE.read_text(encoding="utf-8")
    result = run_flow(source, flow_name="demo")
    assert result.last_value == "ok"

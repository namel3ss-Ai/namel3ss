from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, run_flow

STATE_WRITE_FIXTURE = Path("tests/fixtures/flow_purity_state_write.ai")
TOOL_CALL_FIXTURE = Path("tests/fixtures/flow_purity_tool_call.ai")
CALL_EFFECTFUL_FIXTURE = Path("tests/fixtures/flow_purity_call_effectful.ai")
CALL_PIPELINE_FIXTURE = Path("tests/fixtures/flow_purity_call_pipeline.ai")
EFFECTFUL_CALLS_PURE_FIXTURE = Path("tests/fixtures/flow_purity_effectful_calls_pure.ai")
NO_DECL_FIXTURE = Path("tests/fixtures/flow_purity_no_declaration.ai")
ORCHESTRATION_EFFECTFUL_FIXTURE = Path("tests/fixtures/flow_purity_orchestration_effectful.ai")


def test_pure_flow_state_write_rejected() -> None:
    source = STATE_WRITE_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 10, col 3] What happened: Pure flow \"pure_state\" cannot write state.\n"
        "Why: Pure flows must not perform effects.\n"
        "Fix: Remove the effect or declare the flow as effectful.\n"
        "Example: flow \"demo\": purity is \"effectful\""
    )


def test_pure_flow_tool_call_rejected() -> None:
    source = TOOL_CALL_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 10, col 17] What happened: Pure flow \"pure_tool\" cannot call tool \"summarize\".\n"
        "Why: Pure flows must not perform effects.\n"
        "Fix: Remove the effect or declare the flow as effectful.\n"
        "Example: flow \"demo\": purity is \"effectful\""
    )


def test_pure_flow_calling_effectful_rejected() -> None:
    source = CALL_EFFECTFUL_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 22, col 14] What happened: Pure flow \"pure_caller\" cannot call effectful flow \"effectful\".\n"
        "Why: Pure flows must not perform effects.\n"
        "Fix: Remove the effect or declare the flow as effectful.\n"
        "Example: flow \"demo\": purity is \"effectful\""
    )


def test_pure_flow_calling_pipeline_rejected() -> None:
    source = CALL_PIPELINE_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 13, col 14] What happened: Pure flow \"pure_pipeline\" cannot call effectful pipeline \"ingestion\".\n"
        "Why: Pure flows must not perform effects.\n"
        "Fix: Remove the effect or declare the flow as effectful.\n"
        "Example: flow \"demo\": purity is \"effectful\""
    )


def test_effectful_flow_calling_pure_allowed() -> None:
    source = EFFECTFUL_CALLS_PURE_FIXTURE.read_text(encoding="utf-8")
    result = run_flow(source, flow_name="outer")
    assert result.last_value == {"result": "hello"}


def test_flow_without_purity_unchanged() -> None:
    source = NO_DECL_FIXTURE.read_text(encoding="utf-8")
    result = run_flow(source, flow_name="demo")
    assert result.last_value == "ok"


def test_pure_flow_orchestration_effectful_rejected() -> None:
    source = ORCHESTRATION_EFFECTFUL_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 21, col 7] What happened: Pure flow \"pure_orchestration\" cannot call effectful flow \"effectful\".\n"
        "Why: Pure flows must not perform effects.\n"
        "Fix: Remove the effect or declare the flow as effectful.\n"
        "Example: flow \"demo\": purity is \"effectful\""
    )

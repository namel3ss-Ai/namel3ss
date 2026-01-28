from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program, run_flow

MISSING_INPUT_FIXTURE = Path("tests/fixtures/flow_call_missing_required_input.ai")
EXTRA_INPUT_FIXTURE = Path("tests/fixtures/flow_call_extra_input.ai")
OUTPUT_MISMATCH_FIXTURE = Path("tests/fixtures/flow_call_output_mismatch.ai")
NO_CONTRACT_FIXTURE = Path("tests/fixtures/flow_call_no_contract.ai")


def test_missing_required_input_is_rejected() -> None:
    source = MISSING_INPUT_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 14, col 17] What happened: Missing required inputs: name.\n"
        "Why: All required inputs must be provided.\n"
        "Fix: Add the missing inputs in order.\n"
        "Example: input:\\n  name"
    )


def test_extra_input_is_rejected() -> None:
    source = EXTRA_INPUT_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 14, col 17] What happened: Unknown input \"extra\".\n"
        "Why: The flow contract does not declare this input.\n"
        "Fix: Use the declared input names in order.\n"
        "Example: input:\\n  name"
    )


def test_output_contract_mismatch_is_rejected() -> None:
    source = OUTPUT_MISMATCH_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source, flow_name="outer")
    assert str(excinfo.value) == (
        "[line 14, col 17] error: Runtime error.\n\n"
        "What happened\n"
        "- Runtime error.\n\n"
        "Why\n"
        "- Error message: Missing flow output 'result'\n"
        "- The engine raised an error.\n\n"
        "How to fix\n"
        "- Review the error message and try again.\n\n"
        "Where\n"
        "- flow: outer\n"
        "- statement: let\n"
        "- statement index: 1\n"
        "- line: 14\n"
        "- column: 17\n\n"
        "Error id\n"
        "- E-ENGINE-ENGINE_ERROR-OUTER-LET-1"
    )


def test_flow_without_contract_still_runs() -> None:
    source = NO_CONTRACT_FIXTURE.read_text(encoding="utf-8")
    result = run_flow(source, flow_name="demo")
    assert result.last_value == "ok"

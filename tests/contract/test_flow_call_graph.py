from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program

CYCLE_FIXTURE = Path("tests/fixtures/composition_cycle_indirect.ai")
MISSING_FIXTURE = Path("tests/fixtures/composition_missing_flow.ai")


def test_indirect_cycle_rejected_with_path() -> None:
    source = CYCLE_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert str(excinfo.value) == "[line 40, col 15] Flow call cycle detected: alpha -> beta -> gamma -> alpha"


def test_missing_flow_rejected_with_suggestion() -> None:
    source = MISSING_FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert (
        str(excinfo.value)
        == "[line 8, col 17] What happened: Unknown flow \"alhpa\". Did you mean \"alpha\"?\n"
        "Why: Flow calls must reference declared flows.\n"
        "Fix: Update the call to an existing flow.\n"
        "Example: flow \"alhpa\":\\n  return \"ok\""
    )

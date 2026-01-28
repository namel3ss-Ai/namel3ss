from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program

FIXTURE_PATH = Path("tests/fixtures/composition_recursion.ai")


def test_flow_recursion_is_rejected_deterministically() -> None:
    source = FIXTURE_PATH.read_text(encoding="utf-8")
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert str(excinfo.value) == "[line 25, col 15] Flow call cycle detected: alpha -> beta -> alpha"

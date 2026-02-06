from __future__ import annotations

from namel3ss.spec_check.builder import derive_required_capabilities
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  performance

flow "demo":
  return "ok"
'''


def test_derive_required_capabilities_includes_performance_token_when_declared() -> None:
    program = lower_ir_program(SOURCE)
    required = derive_required_capabilities(program)
    assert "performance" in required

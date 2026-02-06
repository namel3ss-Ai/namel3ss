from __future__ import annotations

from namel3ss.spec_check.builder import derive_required_capabilities
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  streaming

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "demo":
  ask ai "assistant" with stream: true and input: "hello" as reply
  return reply
'''


def test_derive_required_capabilities_includes_streaming_token() -> None:
    program = lower_ir_program(SOURCE)
    required = derive_required_capabilities(program)
    assert "streaming" in required

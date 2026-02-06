from __future__ import annotations

from namel3ss.spec_check.builder import derive_required_capabilities
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  huggingface

ai "assistant":
  model is "huggingface:bert-base-uncased"

flow "demo":
  ask ai "assistant" with input: "hello" as reply
  return reply
'''


def test_derive_required_capabilities_includes_provider_pack_token() -> None:
    program = lower_ir_program(SOURCE)
    required = derive_required_capabilities(program)
    assert "huggingface" in required

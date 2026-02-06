from __future__ import annotations

from namel3ss.spec_check.builder import derive_required_capabilities
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

capabilities:
  vision
  speech

ai "assistant":
  provider is "mock"
  model is "multimodal-model"

flow "demo":
  ask ai "assistant" with image input: "assets/photo.png" as image_reply
  ask ai "assistant" with audio input: "assets/note.wav" as audio_reply
  return audio_reply
'''


def test_derive_required_capabilities_includes_multimodal_tokens() -> None:
    program = lower_ir_program(SOURCE)
    required = derive_required_capabilities(program)
    assert "vision" in required
    assert "speech" in required

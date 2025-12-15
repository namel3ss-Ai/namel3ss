import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_ai_missing_model_errors():
    source = '''ai "assistant":
  system_prompt is "hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "requires a model" in str(exc.value).lower()


def test_unknown_ai_in_ask_errors():
    source = '''flow "demo":
  ask ai "missing" with input: "hi" as reply
'''
    program = lower_ir_program(source)
    with pytest.raises(Namel3ssError) as exc:
        from namel3ss.runtime.executor import execute_program_flow
        execute_program_flow(program, "demo")
    assert "unknown ai" in str(exc.value).lower()


def test_model_not_string_literal_errors():
    source = '''ai "assistant":
  model is state.x
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)

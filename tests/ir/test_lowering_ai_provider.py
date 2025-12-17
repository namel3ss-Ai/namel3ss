import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse


def test_lowering_preserves_provider():
    program = parse(
        '''ai "assistant":
  provider is "ollama"
  model is "llama3.1"
'''
    )
    ir_program = lower_program(program)
    assert ir_program.ais["assistant"].provider == "ollama"


def test_lowering_defaults_to_mock_provider():
    program = parse(
        '''ai "assistant":
  model is "gpt-4.1"
'''
    )
    ir_program = lower_program(program)
    assert ir_program.ais["assistant"].provider == "mock"


def test_lowering_unknown_provider_errors():
    program = parse(
        '''ai "assistant":
  provider is "unknown"
  model is "gpt-4.1"
'''
    )
    with pytest.raises(Namel3ssError):
        lower_program(program)

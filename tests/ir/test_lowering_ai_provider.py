import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse


def test_lowering_preserves_provider():
    program = parse(
        '''spec is "1.0"

ai "assistant":
  provider is "ollama"
  model is "llama3.1"
'''
    )
    ir_program = lower_program(program)
    assert ir_program.ais["assistant"].provider == "ollama"


def test_lowering_defaults_to_mock_provider():
    program = parse(
        '''spec is "1.0"

ai "assistant":
  model is "gpt-4.1"
'''
    )
    ir_program = lower_program(program)
    assert ir_program.ais["assistant"].provider == "mock"


def test_lowering_unknown_provider_errors():
    program = parse(
        '''spec is "1.0"

ai "assistant":
  provider is "unknown"
  model is "gpt-4.1"
'''
    )
    with pytest.raises(Namel3ssError):
        lower_program(program)


def test_lowering_infers_provider_from_model_prefix():
    program = parse(
        '''spec is "1.0"

capabilities:
  huggingface

ai "assistant":
  model is "huggingface:bert-base-uncased"
'''
    )
    ir_program = lower_program(program)
    assert ir_program.ais["assistant"].provider == "huggingface"


def test_lowering_rejects_provider_prefix_mismatch():
    program = parse(
        '''spec is "1.0"

capabilities:
  huggingface

ai "assistant":
  provider is "mistral"
  model is "huggingface:bert-base-uncased"
'''
    )
    with pytest.raises(Namel3ssError) as err:
        lower_program(program)
    assert "does not match model prefix" in str(err.value)

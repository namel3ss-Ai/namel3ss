import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_short_term_invalid_literal():
    source = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    short_term is "10"
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)


def test_short_term_negative():
    source = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    short_term is -1
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)


def test_semantic_invalid_literal():
    source = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    semantic is "yes"
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)


def test_unknown_memory_key():
    source = '''ai "assistant":
  model is "gpt-4.1"
  memory:
    foo is true
'''
    with pytest.raises(Namel3ssError):
        lower_ir_program(source)

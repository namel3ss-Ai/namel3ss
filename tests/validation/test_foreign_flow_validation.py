import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation import ValidationMode
from tests.conftest import lower_ir_program


def test_call_foreign_missing_function() -> None:
    source = '''
flow "demo"
  call foreign "missing"
    amount is 1
'''
    program = lower_ir_program(source)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, config=AppConfig(), mode=ValidationMode.STATIC)
    assert 'Foreign function "missing" is not declared' in str(exc.value)


def test_call_foreign_missing_args() -> None:
    source = '''
foreign python function "calc"
  input
    amount is number
  output is number

flow "demo"
  call foreign "calc"
'''
    program = lower_ir_program(source)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, config=AppConfig(), mode=ValidationMode.STATIC)
    assert "missing input" in str(exc.value)


def test_call_foreign_wrong_type() -> None:
    source = '''
foreign python function "calc"
  input
    amount is number
  output is number

flow "demo"
  call foreign "calc"
    amount is "Ada"
'''
    program = lower_ir_program(source)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, config=AppConfig(), mode=ValidationMode.STATIC)
    assert "expects number" in str(exc.value)

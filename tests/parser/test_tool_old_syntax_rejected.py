import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_old_tool_decl_syntax_rejected():
    source = '''tool "greeter":
  kind is "python"
  entry is "tools.greeter:greet"
  input_schema is json
  output_schema is json

flow "demo":
  return "ok"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Old tool syntax" in str(exc.value)


def test_old_tool_call_syntax_rejected():
    source = '''tool "greeter":
  implemented using python

  input:
    name is text

  output:
    message is text

flow "demo":
  let result is call tool "greeter" with input: input
  return result
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Old tool syntax" in str(exc.value)

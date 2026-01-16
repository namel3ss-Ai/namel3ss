import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


def test_foreign_decl_parse_python_and_js():
    source = '''
foreign python function "calculate_tax"
  input
    amount is number
  output is number

foreign js function "format_currency"
  input
    amount is number
    currency is text
  output is text

flow "demo"
  call foreign "calculate_tax"
    amount is 1
'''
    program = lower_ir_program(source)
    python_fn = program.tools["calculate_tax"]
    js_fn = program.tools["format_currency"]
    assert python_fn.declared_as == "foreign"
    assert python_fn.kind == "python"
    assert python_fn.input_fields[0].name == "amount"
    assert python_fn.output_fields[0].name == "result"
    assert python_fn.output_fields[0].type_name == "number"
    assert js_fn.kind == "node"
    assert js_fn.input_fields[1].name == "currency"
    assert js_fn.output_fields[0].type_name == "text"

    flow = program.flows[0]
    assert flow.declarative is True
    assert any(isinstance(step, ir.FlowCallForeign) for step in flow.steps or [])


def test_foreign_decl_rejects_unknown_type():
    source = '''
foreign python function "bad"
  input
    amount is nuber
  output is number
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    message = str(exc.value)
    assert "Unsupported foreign input type" in message
    assert "number" in message


def test_foreign_decl_rejects_unknown_field():
    source = '''
foreign python function "bad"
  input
    amount is number
  timeout_seconds is 10
  output is number
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Unknown field in foreign function declaration" in str(exc.value)


def test_foreign_decl_rejects_duplicate_names():
    source = '''
foreign python function "dup"
  input
    amount is number
  output is number

foreign js function "dup"
  input
    value is text
  output is text
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Duplicate tool declaration" in str(exc.value)

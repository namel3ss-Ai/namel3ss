from __future__ import annotations

from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

define function "greet":
  input:
    name is text
  output:
    message is optional text
  return map:
    "message" is "hi"

flow "demo":
  let result is call function "greet":
    name is "Ada"
  return result
'''


def test_lower_function_decl_and_call() -> None:
    program = lower_ir_program(SOURCE)
    assert "greet" in program.functions
    func = program.functions["greet"]
    assert func.signature.inputs[0].name == "name"
    assert func.signature.outputs is not None
    output = func.signature.outputs[0]
    assert output.required is False

    flow = program.flows[0]
    stmt = flow.body[0]
    assert isinstance(stmt, ir.Let)
    assert isinstance(stmt.expression, ir.CallFunctionExpr)

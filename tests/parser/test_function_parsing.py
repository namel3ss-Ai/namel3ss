from __future__ import annotations

from namel3ss.ast import nodes as ast
from tests.conftest import parse_program


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


def test_parse_define_function_and_call() -> None:
    program = parse_program(SOURCE)
    assert len(program.functions) == 1
    func = program.functions[0]
    assert func.name == "greet"
    assert func.signature.inputs[0].name == "name"
    assert func.signature.inputs[0].type_name == "text"
    assert func.signature.outputs is not None
    output = func.signature.outputs[0]
    assert output.name == "message"
    assert output.required is False

    flow = program.flows[0]
    stmt = flow.body[0]
    assert isinstance(stmt, ast.Let)
    assert isinstance(stmt.expression, ast.CallFunctionExpr)
    call = stmt.expression
    assert call.function_name == "greet"
    assert call.arguments[0].name == "name"

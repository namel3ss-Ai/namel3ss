from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''tool "greeter":
  implemented using python
  purity is "pure"
  timeout_seconds is 12

  input:
    name is text

  output:
    message is text

spec is "1.0"

flow "demo":
  let result is greeter:
    name is input.name
  return result
'''


def test_tool_decl_and_call_parse():
    program = lower_ir_program(SOURCE)
    tool = program.tools["greeter"]
    assert tool.kind == "python"
    assert tool.input_fields[0].name == "name"
    assert tool.input_fields[0].type_name == "text"
    assert tool.output_fields[0].name == "message"
    assert tool.output_fields[0].type_name == "text"
    assert tool.purity == "pure"
    assert tool.timeout_seconds == 12

    flow = program.flows[0]
    stmt = flow.body[0]
    assert isinstance(stmt, ir.Let)
    assert isinstance(stmt.expression, ir.ToolCallExpr)
    assert stmt.expression.tool_name == "greeter"
    assert stmt.expression.arguments[0].name == "name"

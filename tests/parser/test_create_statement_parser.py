from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''record "Order":
  total number

flow "demo":
  create "Order" with state.order as order
  return order
'''


def test_create_statement_lowers_to_ir():
    program = lower_ir_program(SOURCE)
    stmt = program.flows[0].body[0]
    assert isinstance(stmt, ir.Create)
    assert stmt.record_name == "Order"
    assert stmt.target == "order"

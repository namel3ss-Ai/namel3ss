from __future__ import annotations

from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

flow "demo":
  let value is true or false and false
  let alt is not true or false
  let compare is 1 + 2 * 3 is greater than 6 and true
'''


def test_boolean_precedence_in_ir() -> None:
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]

    expr = flow.body[0].expression
    assert isinstance(expr, ir.BinaryOp)
    assert expr.op == "or"
    assert isinstance(expr.right, ir.BinaryOp)
    assert expr.right.op == "and"

    alt = flow.body[1].expression
    assert isinstance(alt, ir.BinaryOp)
    assert alt.op == "or"
    assert isinstance(alt.left, ir.UnaryOp)
    assert alt.left.op == "not"


def test_comparison_precedence_in_ir() -> None:
    program = lower_ir_program(SOURCE)
    flow = program.flows[0]

    expr = flow.body[2].expression
    assert isinstance(expr, ir.BinaryOp)
    assert expr.op == "and"
    assert isinstance(expr.left, ir.Comparison)
    assert isinstance(expr.left.left, ir.BinaryOp)
    assert expr.left.left.op == "+"
    assert isinstance(expr.left.left.right, ir.BinaryOp)
    assert expr.left.left.right.op == "*"

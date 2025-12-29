from decimal import Decimal

from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

flow "demo":
  let total is 2 + 3 * 4
  let grouped is (2 + 3) * 4
  let neg is -2 + 3
'''


def test_arithmetic_precedence_in_ir():
    program = lower_ir_program(SOURCE)
    expr = program.flows[0].body[0].expression
    assert isinstance(expr, ir.BinaryOp)
    assert expr.op == "+"
    assert isinstance(expr.right, ir.BinaryOp)
    assert expr.right.op == "*"
    assert expr.left.value == Decimal("2")
    assert expr.right.left.value == Decimal("3")


def test_unary_minus_in_ir():
    program = lower_ir_program(SOURCE)
    expr = program.flows[0].body[2].expression
    assert isinstance(expr, ir.BinaryOp)
    assert expr.op == "+"
    assert isinstance(expr.left, ir.UnaryOp)
    assert expr.left.op == "-"


def test_modulo_in_ir():
    source = '''spec is "1.0"

flow "demo":
  let remainder is 10 % 4
'''
    program = lower_ir_program(source)
    expr = program.flows[0].body[0].expression
    assert isinstance(expr, ir.BinaryOp)
    assert expr.op == "%"

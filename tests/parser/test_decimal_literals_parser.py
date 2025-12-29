from decimal import Decimal

from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

flow "demo":
  let total is 10.50
  return total
'''


def test_decimal_literal_lowers_to_decimal_value():
    program = lower_ir_program(SOURCE)
    literal = program.flows[0].body[0].expression
    assert literal.value == Decimal("10.50")

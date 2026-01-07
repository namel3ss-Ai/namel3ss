from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_exponent_integer_result():
    source = '''spec is "1.0"

flow "demo":
  return 2 ** 3
'''
    result = run_flow(source)
    assert result.last_value == Decimal("8")


def test_exponent_fractional_result():
    source = '''spec is "1.0"

flow "demo":
  return 9 ** 0.5
'''
    result = run_flow(source)
    assert result.last_value == Decimal("3")


def test_exponent_float_base():
    source = '''spec is "1.0"

flow "demo":
  return 2.5 ** 2
'''
    result = run_flow(source)
    assert result.last_value == Decimal("6.25")


def test_exponent_unary_minus_precedence():
    source = '''spec is "1.0"

flow "demo":
  return -2 ** 2
'''
    result = run_flow(source)
    assert result.last_value == Decimal("-4")


def test_exponent_parenthesized_base():
    source = '''spec is "1.0"

flow "demo":
  return (-2) ** 2
'''
    result = run_flow(source)
    assert result.last_value == Decimal("4")


def test_exponent_rejects_boolean_operand():
    source = '''spec is "1.0"

flow "demo":
  return true ** 2
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    message = str(excinfo.value)
    assert "Cannot apply '**' to boolean and number." in message


def test_exponent_rejects_text_operand():
    source = '''spec is "1.0"

flow "demo":
  return "x" ** 2
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    message = str(excinfo.value)
    assert "Cannot apply '**' to text and number." in message

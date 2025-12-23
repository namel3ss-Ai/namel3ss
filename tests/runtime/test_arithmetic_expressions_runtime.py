from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_arithmetic_precedence():
    source = '''flow "demo":
  return 2 + 3 * 4
'''
    result = run_flow(source)
    assert result.last_value == Decimal("14")


def test_arithmetic_parentheses():
    source = '''flow "demo":
  return (2 + 3) * 4
'''
    result = run_flow(source)
    assert result.last_value == Decimal("20")


def test_decimal_arithmetic_exact():
    source = '''flow "demo":
  return 0.1 + 0.2
'''
    result = run_flow(source)
    assert result.last_value == Decimal("0.3")


def test_arithmetic_type_error_message():
    source = '''flow "demo":
  return "text" + 2
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    expected = (
        "What happened: Cannot apply '+' to text and number.\n"
        "Why: Arithmetic operators only work on numbers.\n"
        "Fix: Convert both values to numbers or remove the operator.\n"
        "Example: let total is 10.5 + 2.25"
    )
    assert excinfo.value.message == expected


def test_division_by_zero_message():
    source = '''flow "demo":
  return 10 / 0
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    expected = (
        "What happened: Division by zero.\n"
        "Why: The right-hand side of '/' evaluated to 0.\n"
        "Fix: Check for zero before dividing.\n"
        "Example: if divisor is not equal to 0: set state.ratio is total / divisor"
    )
    assert excinfo.value.message == expected

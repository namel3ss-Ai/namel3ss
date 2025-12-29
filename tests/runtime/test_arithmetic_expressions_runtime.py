from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_arithmetic_precedence():
    source = '''spec is "1.0"

flow "demo":
  return 2 + 3 * 4
'''
    result = run_flow(source)
    assert result.last_value == Decimal("14")


def test_arithmetic_parentheses():
    source = '''spec is "1.0"

flow "demo":
  return (2 + 3) * 4
'''
    result = run_flow(source)
    assert result.last_value == Decimal("20")


def test_decimal_arithmetic_exact():
    source = '''spec is "1.0"

flow "demo":
  return 0.1 + 0.2
'''
    result = run_flow(source)
    assert result.last_value == Decimal("0.3")


def test_arithmetic_type_error_message():
    source = '''spec is "1.0"

flow "demo":
  return "text" + 2
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    message = str(excinfo.value)
    assert "error: Cannot apply '+' to text and number." in message
    assert "- Arithmetic operators only work on numbers." in message
    assert "- Convert both values to numbers or remove the operator." in message


def test_division_by_zero_message():
    source = '''spec is "1.0"

flow "demo":
  return 10 / 0
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    message = str(excinfo.value)
    assert "error: Division by zero." in message
    assert "- The right-hand side of '/' evaluated to 0." in message
    assert "- Check for zero before dividing." in message

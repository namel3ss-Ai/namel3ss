from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_function_call_returns_map() -> None:
    source = '''spec is "1.0"

define function "calc":
  input:
    value is number
  output:
    total is number
    note is optional text
  return map:
    "total" is value + 1

flow "demo":
  return call function "calc":
    value is 2
'''
    result = run_flow(source)
    assert isinstance(result.last_value, dict)
    assert result.last_value.get("total") == Decimal("3")
    assert "note" not in result.last_value


def test_function_missing_required_output() -> None:
    source = '''spec is "1.0"

define function "calc":
  input:
    value is number
  output:
    total is number
  return map:
    "note" is "x"

flow "demo":
  return call function "calc":
    value is 2
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    assert "Missing function output" in str(excinfo.value)

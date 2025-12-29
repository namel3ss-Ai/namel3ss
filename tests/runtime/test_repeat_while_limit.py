from __future__ import annotations

from decimal import Decimal

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


def test_repeat_while_exits_before_limit() -> None:
    source = '''spec is "1.0"

flow "demo":
  let count is 0
  repeat while count is less than 2 limit 3:
    set count is count + 1
  return count
'''
    result = run_flow(source)
    assert result.last_value == Decimal("2")


def test_repeat_while_hits_limit() -> None:
    source = '''spec is "1.0"

flow "demo":
  let count is 0
  repeat while count is less than 5 limit 2:
    set count is count + 1
  return count
'''
    with pytest.raises(Namel3ssError) as excinfo:
        run_flow(source)
    assert "Loop limit hit" in str(excinfo.value)

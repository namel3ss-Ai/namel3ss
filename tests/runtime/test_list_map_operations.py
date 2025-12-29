from __future__ import annotations

from decimal import Decimal

from tests.conftest import run_flow


def test_list_ops_and_map_literal() -> None:
    source = '''spec is "1.0"

flow "demo":
  let numbers is list:
    1
    2
  let appended is list append numbers with 3
  let size is list length of appended
  let first is list get appended at 0
  return map:
    "size" is size
    "first" is first
'''
    result = run_flow(source)
    assert result.last_value == {"size": 3, "first": Decimal("1")}


def test_map_ops_and_key_ordering() -> None:
    source = '''spec is "1.0"

flow "demo":
  let data is map:
    "b" is 1
    "a" is 2
  let updated is map set data key "c" value 3
  let keys is map keys updated
  let first is list get keys at 0
  let value_b is map get updated key "b"
  return map:
    "first" is first
    "value" is value_b
'''
    result = run_flow(source)
    assert result.last_value.get("first") == "a"
    assert result.last_value.get("value") == Decimal("1")

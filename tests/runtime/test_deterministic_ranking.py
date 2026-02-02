from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import run_flow


ORDER_SOURCE = '''spec is "1.0"

flow "demo":
  let items is list:
    map:
      "id" is "a"
      "score" is 2
    map:
      "id" is "b"
      "score" is 5
    map:
      "id" is "c"
      "score" is 5
    map:
      "id" is "d"
      "score" is 1
  set state.items is items
  order state.items by score from highest to lowest
  keep first 3 items
  return state.items
'''


def test_order_desc_with_ties_is_stable():
    result = run_flow(ORDER_SOURCE)
    assert result.last_value == [
        {"id": "b", "score": 5},
        {"id": "c", "score": 5},
        {"id": "a", "score": 2},
    ]


def test_order_asc_keeps_original_order_for_equal_scores():
    source = '''spec is "1.0"

flow "demo":
  let items is list:
    map:
      "name" is "first"
      "score" is 1
    map:
      "name" is "second"
      "score" is 1
    map:
      "name" is "third"
      "score" is 2
  set state.items is items
  order state.items by score from lowest to highest
  return state.items
'''
    result = run_flow(source)
    assert result.last_value == [
        {"name": "first", "score": 1},
        {"name": "second", "score": 1},
        {"name": "third", "score": 2},
    ]


def test_keep_first_smaller_than_list():
    source = '''spec is "1.0"

flow "demo":
  let items is list:
    map:
      "id" is "a"
      "score" is 3
    map:
      "id" is "b"
      "score" is 4
  set state.items is items
  order state.items by score from highest to lowest
  keep first 5 items
  return state.items
'''
    result = run_flow(source)
    assert result.last_value == [
        {"id": "b", "score": 4},
        {"id": "a", "score": 3},
    ]


def test_order_empty_list_is_stable():
    source = '''spec is "1.0"

flow "demo":
  let items is list:
  set state.items is items
  order state.items by score from highest to lowest
  keep first 2 items
  return state.items
'''
    result = run_flow(source)
    assert result.last_value == []


def test_keep_first_requires_order():
    source = '''spec is "1.0"

flow "demo":
  let items is list:
    map:
      "id" is "a"
      "score" is 1
  set state.items is items
  keep first 1 items
  return state.items
'''
    with pytest.raises(Namel3ssError) as exc:
        run_flow(source)
    assert "order statement" in str(exc.value)

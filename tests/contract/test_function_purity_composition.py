from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_function_cannot_call_flow() -> None:
    source = '''spec is "1.0"

contract flow "inner":
  input:
    name is text
  output:
    result is text

flow "inner":
  return map:
    "result" is "ok"

define function "calc":
  input:
    name is text
  output:
    result is text
  return call flow "inner":
    input:
      name is name
    output:
      result

flow "demo":
  return "ok"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert "Functions cannot call flows" in str(excinfo.value)


def test_function_cannot_call_pipeline() -> None:
    source = '''spec is "1.0"

define function "calc":
  input:
    query is text
  output:
    report is json
  return call pipeline "retrieval":
    input:
      query is query
    output:
      report

flow "demo":
  return "ok"
'''
    with pytest.raises(Namel3ssError) as excinfo:
        lower_ir_program(source)
    assert "Functions cannot call pipelines" in str(excinfo.value)

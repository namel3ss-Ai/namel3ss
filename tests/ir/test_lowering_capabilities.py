import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_missing_http_capability_rejected() -> None:
    source = '''spec is "1.0"

tool "fetch":
  implemented using http

  input:
    url is text

  output:
    status is number

flow "demo":
  let response is fetch:
    url is "https://example.com"
  return response
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message


def test_missing_jobs_capability_rejected() -> None:
    source = '''spec is "1.0"

job "refresh":
  return "ok"

flow "demo":
  return "ok"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "Missing capabilities" in exc.value.message


def test_capabilities_allow_http_and_jobs() -> None:
    source = '''spec is "1.0"

capabilities:
  jobs
  http

tool "fetch":
  implemented using http

  input:
    url is text

  output:
    status is number

job "refresh":
  return "ok"

flow "demo":
  enqueue job "refresh"
  let response is fetch:
    url is "https://example.com"
  return response
'''
    program = lower_ir_program(source)
    assert program.capabilities == ("http", "jobs")

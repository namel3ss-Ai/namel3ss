from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import lower_ir_program


def test_lower_routes_and_ai_metadata() -> None:
    source = '''
record "User":
  id number

flow "get_user":
  ai:
    model is "gpt-4"
    prompt is "Summarise: {state.input.text}"
  return "ok"

route "get_user":
  path is "/api/users/{id}"
  method is "GET"
  parameters:
    id is number
  request:
    id is number
  response:
    result is User
  flow is "get_user"
'''.lstrip()
    program = lower_ir_program(source)
    assert len(program.routes) == 1
    route = program.routes[0]
    assert route.method == "GET"
    assert route.parameters["id"].type_name == "number"
    assert route.response["result"].type_name == "User"
    flow = program.flows[0]
    assert flow.ai_metadata is not None
    assert flow.ai_metadata.model == "gpt-4"


def test_route_unknown_flow_errors() -> None:
    source = '''
flow "demo":
  return "ok"

route "missing_flow":
  path is "/api/missing"
  method is "GET"
  request:
    id is number
  response:
    ok is boolean
  flow is "does_not_exist"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown flow" in str(exc.value).lower()


def test_route_missing_request_errors() -> None:
    source = '''
flow "demo":
  return "ok"

route "missing_request":
  path is "/api/missing"
  method is "GET"
  response:
    ok is boolean
  flow is "demo"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "missing a request block" in str(exc.value).lower()


def test_route_unknown_type_errors() -> None:
    source = '''
flow "demo":
  return "ok"

route "bad_type":
  path is "/api/bad"
  method is "GET"
  request:
    id is number
  response:
    result is MissingRecord
  flow is "demo"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown route type" in str(exc.value).lower()

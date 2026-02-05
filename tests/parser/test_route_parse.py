from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_parse_route_declaration() -> None:
    source = '''
record "User":
  id number

flow "get_users":
  return "ok"

route "list_users":
  path is "/api/users"
  method is "GET"
  parameters:
    page_number is number
    tags is list<text>
  request:
    filter is text
  response:
    users is list<User>
  flow is "get_users"
  upload is true
'''.lstrip()
    program = parse_program(source)
    assert len(program.routes) == 1
    route = program.routes[0]
    assert route.name == "list_users"
    assert route.path == "/api/users"
    assert route.method == "GET"
    assert route.flow_name == "get_users"
    assert route.upload is True
    assert route.parameters["page_number"].type_name == "number"
    assert route.parameters["tags"].type_name == "list<text>"
    assert route.request["filter"].type_name == "text"
    assert route.response["users"].type_name == "list<User>"


def test_route_missing_response_errors() -> None:
    source = '''
flow "get_users":
  return "ok"

route "list_users":
  path is "/api/users"
  method is "GET"
  flow is "get_users"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Route is missing a response block" in str(exc.value)


def test_route_invalid_method_errors() -> None:
    source = '''
flow "get_users":
  return "ok"

route "list_users":
  path is "/api/users"
  method is "FETCH"
  response:
    ok is boolean
  flow is "get_users"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Unsupported HTTP method" in str(exc.value)

from __future__ import annotations

from tests.conftest import run_flow


BASE_SOURCE = '''
flow "demo":
  return "ok"
'''.lstrip()

META_SOURCE = '''
flow "demo":
  ai:
    model is "gpt-4"
    prompt is "Hello world"
  return "ok"

route "demo_route":
  path is "/api/demo"
  method is "GET"
  request:
    payload is json
  response:
    result is text
  flow is "demo"
'''.lstrip()


def test_route_and_ai_metadata_do_not_change_flow_output() -> None:
    base_result = run_flow(BASE_SOURCE)
    meta_result = run_flow(META_SOURCE)
    assert base_result.last_value == meta_result.last_value


CRUD_SOURCE = '''
record "User":
  id number
  name text

crud "User"

prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."

llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text

flow "create_user":
  return "ok"

flow "read_user":
  return "ok"

flow "update_user":
  return "ok"

flow "delete_user":
  return "ok"

flow "demo":
  return "ok"
'''.lstrip()


def test_crud_and_ai_flow_metadata_do_not_change_flow_output() -> None:
    base_result = run_flow(BASE_SOURCE)
    meta_result = run_flow(CRUD_SOURCE)
    assert base_result.last_value == meta_result.last_value

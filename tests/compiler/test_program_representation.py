from __future__ import annotations

from pathlib import Path

from namel3ss.compiler import (
    PROGRAM_REPRESENTATION_SCHEMA,
    build_program_representation,
    program_representation_to_json,
    program_representation_to_payload,
)
from namel3ss.module_loader import load_project


APP = '''spec is "1.0"

record "User" version "1.0":
  id number
  name text

flow "list_users":
  return "ok"

route "list_users_route":
  path is "/users"
  method is "GET"
  request:
    input_text is text
  response:
    result is text
  flow is "list_users"
'''


def test_program_representation_payload_is_stable(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP, encoding="utf-8")
    project = load_project(app_path)

    representation = build_program_representation(project.app_ast)
    payload = program_representation_to_payload(representation)

    assert representation.spec_version == "1.0"
    assert isinstance(payload, dict)
    assert payload["records"][0]["name"] == "User"
    assert payload["flows"][0]["name"] == "list_users"
    assert payload["routes"][0]["name"] == "list_users_route"
    assert PROGRAM_REPRESENTATION_SCHEMA == "program_representation.v1"


def test_program_representation_json_is_deterministic(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(APP, encoding="utf-8")
    project = load_project(app_path)

    representation = build_program_representation(project.app_ast)
    first = program_representation_to_json(representation, pretty=True)
    second = program_representation_to_json(representation, pretty=True)

    assert first == second
    assert '"spec_version": "1.0"' in first
    assert '"name": "list_users"' in first

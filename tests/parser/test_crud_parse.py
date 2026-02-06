from __future__ import annotations

from tests.conftest import parse_program


def test_parse_crud_declaration_expands_routes() -> None:
    source = '''
record "UserProfile":
  id number
  name text

crud "UserProfile"
'''.lstrip()
    program = parse_program(source)
    assert len(program.crud) == 1
    assert program.crud[0].record_name == "UserProfile"
    routes = {route.name: route for route in program.routes}
    assert set(routes.keys()) == {"create_user_profile", "read_user_profile", "update_user_profile", "delete_user_profile"}
    create = routes["create_user_profile"]
    assert create.generated is True
    assert create.path == "/api/user_profiles"
    assert create.method == "POST"
    assert create.request["body"].type_name == "UserProfile"
    assert create.response["user_profile"].type_name == "UserProfile"
    read = routes["read_user_profile"]
    assert read.path == "/api/user_profiles/{id}"
    assert read.method == "GET"
    assert read.parameters["id"].type_name == "number"
    assert read.request["id"].type_name == "number"
    delete = routes["delete_user_profile"]
    assert delete.request["id"].type_name == "number"

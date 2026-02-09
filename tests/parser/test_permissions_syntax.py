import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def _as_matrix(declaration: ast.AppPermissionsDecl) -> dict[str, bool]:
    matrix: dict[str, bool] = {}
    for domain in declaration.domains:
        for action in domain.actions:
            matrix[f"{domain.domain}.{action.action}"] = bool(action.allowed)
    return matrix


def test_permissions_block_parses_allowed_and_denied() -> None:
    source = '''spec is "1.0"

permissions:
  ai:
    call: allowed
    tools: denied
  uploads:
    read: allowed
  ui_state:
    persistent_write: denied

page "Home":
  text is "Ready"
'''
    program = parse_program(source)
    declaration = getattr(program, "app_permissions", None)
    assert isinstance(declaration, ast.AppPermissionsDecl)
    matrix = _as_matrix(declaration)
    assert matrix["ai.call"] is True
    assert matrix["ai.tools"] is False
    assert matrix["uploads.read"] is True
    assert matrix["ui_state.persistent_write"] is False


def test_permissions_rejects_unknown_domain() -> None:
    source = '''spec is "1.0"

permissions:
  unknown_domain:
    call: allowed

page "Home":
  text is "Ready"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "Unknown permissions domain" in str(exc.value)


def test_permissions_rejects_duplicate_domain() -> None:
    source = '''spec is "1.0"

permissions:
  ai:
    call: allowed
  ai:
    tools: denied

page "Home":
  text is "Ready"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "already declared" in str(exc.value)

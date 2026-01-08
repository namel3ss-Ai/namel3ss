import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


ORDER_SOURCE = '''flow "run":
  return "ok"

page "home":
  button "Second":
    calls flow "run"
  button "First":
    calls flow "run"
'''


DUPLICATE_SOURCE = '''flow "run":
  return "ok"

page "home":
  button "Run":
    calls flow "run"
  button "Run":
    calls flow "run"
'''


def test_manifest_actions_sorted_by_id():
    program = lower_ir_program(ORDER_SOURCE)
    manifest = build_manifest(program, state={})
    keys = list(manifest["actions"].keys())
    assert keys == sorted(keys)


def test_manifest_action_id_collision_errors():
    program = lower_ir_program(DUPLICATE_SOURCE)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={})
    assert "duplicated" in str(exc.value).lower()

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


ORDER_SOURCE = '''flow "run_flow":
  return "ok"

page "home":
  button "Second":
    calls flow "run_flow"
  button "First":
    calls flow "run_flow"
'''


DUPLICATE_SOURCE = '''flow "run_flow":
  return "ok"

page "home":
  button "Run":
    calls flow "run_flow"
  button "Run":
    calls flow "run_flow"
'''


def test_manifest_actions_sorted_by_id():
    program = lower_ir_program(ORDER_SOURCE)
    manifest = build_manifest(program, state={})
    keys = list(manifest["actions"].keys())
    assert keys == sorted(keys)


def test_manifest_action_id_collision_errors():
    program = lower_ir_program(DUPLICATE_SOURCE)
    manifest = build_manifest(program, state={})
    action_ids = list(manifest["actions"].keys())
    assert len(action_ids) == len(set(action_ids))
    assert "page.home.button.run" in action_ids
    assert "page.home.button.run__page.home.button_item.1" in action_ids

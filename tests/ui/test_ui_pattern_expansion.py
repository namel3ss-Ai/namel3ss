from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


FIXTURE_APP = Path("tests/fixtures/ui_patterns_app.ai")


def test_ui_pattern_unknown_errors():
    source = '''page "home":
  use pattern "Missing"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown pattern" in str(exc.value).lower()


def test_ui_pattern_invalid_argument_type():
    source = '''page "home":
  use pattern "Empty State":
    heading is 5
    guidance is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "pattern argument 'heading' must be text" in str(exc.value).lower()


def test_ui_pattern_missing_required_argument():
    source = '''page "home":
  use pattern "Empty State":
    heading is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "required for pattern 'empty state'" in str(exc.value).lower()


def test_ui_pattern_unknown_argument():
    source = '''page "home":
  use pattern "Empty State":
    heading is "Hi"
    guidance is "There"
    extra is "Nope"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "pattern argument 'extra' is not declared" in str(exc.value).lower()


def test_ui_pattern_state_argument_disallowed():
    source = '''page "home":
  use pattern "Empty State":
    heading is state.ready
    guidance is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "pattern arguments must be literal values" in str(exc.value).lower()


def test_ui_pattern_rejects_non_ui_declarations():
    source = '''pattern "Bad":
  flow "run_flow":
    return "ok"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unexpected item 'flow'" in str(exc.value).lower()


def test_ui_pattern_rejects_state_parameter_type():
    source = '''pattern "Bad":
  parameters:
    flag is state
  text is "Hi"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unsupported parameter type" in str(exc.value).lower()


def test_ui_pattern_visibility_combined_errors():
    source = '''pattern "Gate":
  text is "Hi" visibility is state.ready

page "home":
  use pattern "Gate" visibility is state.show
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "pattern visibility cannot be combined" in str(exc.value).lower()


def test_ui_pattern_visibility_expands_actions():
    source = '''flow "run_flow":
  return "ok"

pattern "Gate":
  section:
    button "Run":
      calls flow "run_flow"

page "home":
  use pattern "Gate" visibility is state.ready
'''
    program = lower_ir_program(source)
    hidden = build_manifest(program, state={"ready": False}, store=None)
    section = hidden["pages"][0]["elements"][0]
    assert section["type"] == "section"
    assert section["visible"] is False
    assert hidden["actions"] == {}

    visible = build_manifest(program, state={"ready": True}, store=None)
    section = visible["pages"][0]["elements"][0]
    button = section["children"][0]
    assert section["visible"] is True
    assert button.get("visible", True) is True
    assert any(action.get("type") == "call_flow" for action in visible["actions"].values())


def test_ui_pattern_manifest_is_deterministic():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)
    assert first == second


def test_ui_pattern_origin_does_not_include_host_paths(tmp_path: Path):
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    program.project_root = str(tmp_path)
    manifest = build_manifest(program, state={}, store=None)
    payload = json.dumps(manifest, sort_keys=True)
    raw = str(tmp_path)
    assert raw not in payload
    assert raw.replace("\\", "\\\\") not in payload
    assert tmp_path.as_posix() not in payload


def test_ui_pattern_origin_includes_parameters():
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state={}, store=None)
    elements = manifest["pages"][0]["elements"]
    status_block = elements[0]
    origin = status_block.get("origin") or {}
    params = origin.get("parameters") or {}
    assert params.get("heading") == "Ready"
    assert params.get("guidance") == "Waiting"

from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ui.explain.build_core import _build_pages
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE_ACTIONS = '''flow "run_flow":
  return "ok"

page "home":
  title is "Ready" visibility is state.ready
  button "Run" visibility is state.ready:
    calls flow "run_flow"
'''


SOURCE_ONLY_WHEN = '''flow "run_flow":
  return "ok"

page "home":
  title is "Ready"
    only when state.status is "ready"
  button "Run":
    calls flow "run_flow"
    only when state.status is "ready"
'''


def test_visibility_evaluates_and_filters_actions():
    program = lower_ir_program(SOURCE_ACTIONS)
    hidden = build_manifest(program, state={"ready": False}, store=None)
    elements = hidden["pages"][0]["elements"]
    title = next(el for el in elements if el.get("type") == "title")
    button = next(el for el in elements if el.get("type") == "button")
    assert title["visible"] is False
    assert title["visibility"]["predicate"] == "state.ready"
    assert title["visibility"]["result"] is False
    assert button["visible"] is False
    assert hidden["actions"] == {}

    visible = build_manifest(program, state={"ready": True}, store=None)
    elements = visible["pages"][0]["elements"]
    title = next(el for el in elements if el.get("type") == "title")
    button = next(el for el in elements if el.get("type") == "button")
    assert title["visible"] is True
    assert title["visibility"]["result"] is True
    assert button["visible"] is True
    assert any(action.get("type") == "call_flow" for action in visible["actions"].values())


def test_only_when_evaluates_and_filters_actions():
    program = lower_ir_program(SOURCE_ONLY_WHEN)
    program.state_defaults = {"status": "loading"}
    hidden = build_manifest(program, state={"status": "loading"}, store=None)
    elements = hidden["pages"][0]["elements"]
    title = next(el for el in elements if el.get("type") == "title")
    button = next(el for el in elements if el.get("type") == "button")
    assert title["visible"] is False
    assert title["visibility"]["predicate"] == 'state.status is "ready"'
    assert title["visibility"]["result"] is False
    assert button["visible"] is False
    assert hidden["actions"] == {}

    visible = build_manifest(program, state={"status": "ready"}, store=None)
    elements = visible["pages"][0]["elements"]
    title = next(el for el in elements if el.get("type") == "title")
    button = next(el for el in elements if el.get("type") == "button")
    assert title["visible"] is True
    assert title["visibility"]["result"] is True
    assert button["visible"] is True
    assert any(action.get("type") == "call_flow" for action in visible["actions"].values())


def test_only_when_is_deterministic():
    program = lower_ir_program(SOURCE_ONLY_WHEN)
    program.state_defaults = {"status": "ready"}
    first = build_manifest(program, state={"status": "ready"}, store=None)
    second = build_manifest(program, state={"status": "ready"}, store=None)
    assert first == second


def test_visibility_explain_reasons_include_predicate_and_result():
    source = '''page "home":
  section "Gate" visibility is state.ready:
    text is "Inside"
'''
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={"ready": False}, store=None)
    _, pages = _build_pages(manifest, actions=[])
    elements = pages[0]["elements"]
    section = next(el for el in elements if el.get("kind") == "section")
    text = next(el for el in elements if el.get("kind") == "text")
    assert section["visible"] is False
    assert "visibility predicate state.ready" in section["reasons"]
    assert "visibility paths state.ready" in section["reasons"]
    assert "visibility result false" in section["reasons"]
    assert "hidden because visibility result is false" in section["reasons"]
    assert text["visible"] is False
    assert "hidden because parent visibility is false" in text["reasons"]


@pytest.mark.parametrize(
    "source, message",
    [
        ('page "home":\n  title is "Hi" visibility is input.ready\n', "Visibility requires state.<path>."),
        ('page "home":\n  title is "Hi" visibility is state\n', "Visibility requires state.<path>."),
        ('page "home":\n  title is "Hi" visibility is state.ready and state.other\n', "Visibility only supports a state path."),
    ],
)
def test_visibility_rejects_invalid_forms(source, message):
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert message in str(exc.value)


def test_visibility_build_does_not_create_runtime_artifacts(tmp_path: Path):
    source = 'page "home":\n  title is "Ready" visibility is state.ready\n'
    program = lower_ir_program(source)
    program.project_root = str(tmp_path)
    manifest = build_manifest(program, state={"ready": True}, store=None)
    assert manifest["pages"]
    assert list(tmp_path.iterdir()) == []


def test_only_when_missing_state_path_errors():
    source = '''page "home":
  title is "Hi"
    only when state.status is "ready"
'''
    program = lower_ir_program(source)
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={}, store=None)
    assert "Visibility rule requires declared state path 'state.status'." in str(exc.value)


def test_only_when_type_mismatch_errors():
    source = '''page "home":
  title is "Hi"
    only when state.status is "ready"
'''
    program = lower_ir_program(source)
    program.state_defaults = {"status": True}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={}, store=None)
    assert "expects text but state value is boolean" in str(exc.value)

from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE_STATUS = '''page "home":
  status:
    loading when state.status is loading
      text is "Loading"
    empty when state.items is empty
      text is "No results"
    error when state.status is error
      text is "Something went wrong"
  title is "Main"
  text is "Content"
'''


def _element_pairs(manifest: dict) -> list[tuple[str, str | None]]:
    return [(el.get("type"), el.get("value")) for el in manifest["pages"][0]["elements"]]


def test_status_loading_renders_first():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready", "items": []}
    manifest = build_manifest(program, state={"status": "loading", "items": [1]}, store=None)
    assert _element_pairs(manifest) == [("text", "Loading")]


def test_status_empty_renders_when_collection_empty():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready", "items": []}
    manifest = build_manifest(program, state={"status": "ready", "items": []}, store=None)
    assert _element_pairs(manifest) == [("text", "No results")]


def test_status_error_renders_when_status_matches():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready", "items": []}
    manifest = build_manifest(program, state={"status": "error", "items": [1]}, store=None)
    assert _element_pairs(manifest) == [("text", "Something went wrong")]


def test_status_falls_back_to_normal_ui():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready", "items": []}
    manifest = build_manifest(program, state={"status": "ready", "items": [1]}, store=None)
    assert _element_pairs(manifest) == [("title", "Main"), ("text", "Content")]


def test_status_multiple_matches_fail():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready", "items": []}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"status": "loading", "items": []}, store=None)
    assert "Status block matches multiple entries: loading, empty." in str(exc.value)


def test_status_empty_requires_collection_type():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready", "items": "none"}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"status": "ready"}, store=None)
    assert "expects a list or map" in str(exc.value)


def test_status_missing_state_path_errors():
    program = lower_ir_program(SOURCE_STATUS)
    program.state_defaults = {"status": "ready"}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"status": "ready"}, store=None)
    assert "requires declared state path 'state.items'" in str(exc.value)

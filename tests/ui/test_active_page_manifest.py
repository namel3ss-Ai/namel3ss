from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''ui:
  pages:
    active page:
      is "home" only when state.page is "home"
      is "results" only when state.page is "results"

page "home":
  title is "Home"

page "results":
  title is "Results"
'''


def _build(state: dict) -> dict:
    program = lower_ir_program(SOURCE)
    program.state_defaults = {"page": "home"}
    return build_manifest(program, state=state, store=None)


def test_active_page_selects_matching_rule():
    manifest = _build({"page": "results"})
    active = manifest["navigation"]["active_page"]
    assert active["name"] == "results"
    assert active["source"] == "rule"
    assert active["predicate"] == 'state.page is "results"'


def test_active_page_defaults_to_first_page():
    manifest = _build({"page": "other"})
    active = manifest["navigation"]["active_page"]
    assert active["name"] == "home"
    assert active["source"] == "default"


def test_active_page_requires_declared_state_path():
    program = lower_ir_program(SOURCE)
    program.state_defaults = {"other": "home"}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state={"page": "home"}, store=None)
    assert "declared state path 'state.page'" in str(exc.value)


def test_active_page_unknown_page_errors():
    source = '''ui:
  pages:
    active page:
      is "missing" only when state.page is "missing"

page "home":
  title is "Home"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown page" in str(exc.value).lower()


def test_active_page_duplicate_rule_errors():
    source = '''ui:
  pages:
    active page:
      is "home" only when state.page is "ready"
      is "results" only when state.page is "ready"

page "home":
  title is "Home"

page "results":
  title is "Results"
'''
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "must be unique" in str(exc.value).lower()


def test_active_page_is_deterministic():
    first = _build({"page": "results"})
    second = _build({"page": "results"})
    assert first == second


def test_navigation_absent_without_active_page_rules():
    source = 'page "home":\n  title is "Home"\n'
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=None)
    assert "navigation" not in manifest

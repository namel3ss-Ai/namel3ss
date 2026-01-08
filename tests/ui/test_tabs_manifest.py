from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''record "Order":
  name text

page "home":
  tabs:
    tab "Overview":
      text is "Hi"
    tab "Orders":
      table is "Order"
'''


DEFAULT_SOURCE = '''page "home":
  tabs:
    default is "Second"
    tab "First":
      text is "One"
    tab "Second":
      text is "Two"
'''


def test_tabs_manifest_defaults_to_first_tab():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={})
    assert manifest == build_manifest(program, state={})
    tabs = manifest["pages"][0]["elements"][0]
    assert tabs["type"] == "tabs"
    assert tabs["default"] == "Overview"
    assert tabs["active"] == "Overview"
    assert tabs["tabs"] == ["Overview", "Orders"]


def test_tabs_manifest_respects_explicit_default():
    program = lower_ir_program(DEFAULT_SOURCE)
    manifest = build_manifest(program, state={})
    tabs = manifest["pages"][0]["elements"][0]
    assert tabs["default"] == "Second"
    assert tabs["active"] == "Second"

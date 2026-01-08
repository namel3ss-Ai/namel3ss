from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''ui_pack "widgets":
  version is "1.2.3"
  fragment "summary":
    section "Stats":
      text is "Hello"

page "home":
  use ui_pack "widgets" fragment "summary"
'''


def test_ui_pack_manifest_includes_origin():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state={})
    page = manifest["pages"][0]
    section = page["elements"][0]
    assert section["origin"] == {"pack": "widgets", "version": "1.2.3", "fragment": "summary"}
    assert list(section["origin"].keys()) == ["pack", "version", "fragment"]
    child = section["children"][0]
    assert child["origin"]["pack"] == "widgets"

from namel3ss.page_layout import PAGE_LAYOUT_SLOT_ORDER
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


LAYOUT_SOURCE = '''spec is "1.0"

flow "send":
  return "ok"

page "chat":
  layout:
    header:
      title is "Chat"
    sidebar_left:
      section "Threads":
        list from state threads:
          item:
            primary is name
    main:
      section "Conversation":
        chat:
          messages from is state.messages
          composer calls flow "send"
    drawer_right:
      section "Details":
        text is "Context"
    footer:
      text is "v1.0"
'''

LEGACY_SOURCE = '''spec is "1.0"

page "home":
  title is "Home"
  text is "Legacy stack"
'''


def test_manifest_emits_layout_object_for_layout_pages():
    manifest = build_manifest(lower_ir_program(LAYOUT_SOURCE), state={})
    page = manifest["pages"][0]
    assert "layout" in page
    assert "elements" not in page
    assert list(page["layout"].keys()) == list(PAGE_LAYOUT_SLOT_ORDER)
    assert page["layout"]["header"][0]["type"] == "title"
    assert page["layout"]["sidebar_left"][0]["type"] == "section"
    assert page["layout"]["main"][0]["type"] == "section"
    assert page["layout"]["drawer_right"][0]["type"] == "section"
    assert page["layout"]["footer"][0]["type"] == "text"


def test_manifest_layout_generation_is_deterministic():
    program = lower_ir_program(LAYOUT_SOURCE)
    first = build_manifest(program, state={})
    second = build_manifest(program, state={})
    assert first == second


def test_legacy_pages_still_emit_elements():
    manifest = build_manifest(lower_ir_program(LEGACY_SOURCE), state={})
    page = manifest["pages"][0]
    assert "elements" in page
    assert "layout" not in page

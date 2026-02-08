from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


LAYOUT_SOURCE = '''spec is "1.0"

flow "reply":
  return "ok"

page "support":
  layout:
    header:
      title is "Support Inbox"
    sidebar_left:
      section "Folders":
        text is "Open"
    main:
      section "Messages":
        chat:
          messages from is state.messages
          composer calls flow "reply"
    drawer_right:
      section "Details":
        text is "Metadata"
    footer:
      text is "Powered by Namel3ss"
'''


def test_lowering_preserves_layout_slots():
    program = lower_ir_program(LAYOUT_SOURCE)
    page = program.pages[0]
    assert isinstance(page.layout, ir.PageLayout)
    assert isinstance(page.layout.header[0], ir.TitleItem)
    assert isinstance(page.layout.sidebar_left[0], ir.SectionItem)
    assert isinstance(page.layout.main[0], ir.SectionItem)
    assert isinstance(page.layout.drawer_right[0], ir.SectionItem)
    assert isinstance(page.layout.footer[0], ir.TextItem)
    assert len(page.items) == 5

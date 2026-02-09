from namel3ss.ir import nodes as ir
from tests.conftest import lower_ir_program


SOURCE = '''capabilities:
  ui_rag

flow "answer_question":
  return "ok"

page "RAG":
  rag_ui:
    features: conversation, evidence
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
'''


def test_rag_ui_expands_to_layout_nodes() -> None:
    program = lower_ir_program(SOURCE)
    page = program.pages[0]
    assert page.items
    root = page.items[0]
    assert isinstance(root, ir.LayoutStack)
    sidebar_layout = next((child for child in root.children if isinstance(child, ir.SidebarLayout)), None)
    assert isinstance(sidebar_layout, ir.SidebarLayout)
    main_row = sidebar_layout.main[0]
    assert isinstance(main_row, ir.LayoutRow)
    drawer = next((child for child in main_row.children if isinstance(child, ir.LayoutDrawer)), None)
    assert isinstance(drawer, ir.LayoutDrawer)
    origin = getattr(drawer, "origin", None)
    assert isinstance(origin, dict)
    assert "rag_ui" in origin

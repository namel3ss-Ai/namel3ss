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


MINIMAL_RESEARCH_SOURCE = '''capabilities:
  ui_rag

flow "answer_question":
  return "ok"

page "RAG":
  rag_ui:
    base is "research"
    binds:
      on_send calls flow "answer_question"
'''


MINIMAL_RESEARCH_NO_BINDS_SOURCE = '''capabilities:
  ui_rag

flow "ask_question":
  return "ok"

page "RAG":
  rag_ui:
    base is "research"
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


def test_rag_ui_expands_shell_selectors_with_binding_origin() -> None:
    source = '''capabilities:
  ui_rag

flow "answer_question":
  return "ok"

page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      threads from is state.chat.threads
      active_thread when is state.chat.active_thread
      models from is state.chat.models
      active_models when is state.chat.active_models
      composer_state when is state.chat.composer_state
'''
    program = lower_ir_program(source)
    page = program.pages[0]
    selectors: list[ir.ScopeSelectorItem] = []
    for item in _walk_page_items(page.items):
        if isinstance(item, ir.ScopeSelectorItem):
            selectors.append(item)
    by_binding = {
        ((getattr(item, "origin", {}) or {}).get("rag_ui", {}) or {}).get("binding"): item for item in selectors
    }
    assert "threads" in by_binding
    assert "models" in by_binding
    assert (by_binding["threads"].origin["rag_ui"]).get("selection") == "single"
    assert (by_binding["models"].origin["rag_ui"]).get("selection") == "multi"
    composer = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatComposerItem)), None)
    assert isinstance(composer, ir.ChatComposerItem)
    rag_origin = (getattr(composer, "origin", {}) or {}).get("rag_ui", {})
    assert rag_origin.get("binding") == "composer_state"
    assert rag_origin.get("state_path") == ["chat", "composer_state"]


def test_rag_ui_research_defaults_expand_when_binds_are_omitted() -> None:
    program = lower_ir_program(MINIMAL_RESEARCH_SOURCE)
    page = program.pages[0]
    messages = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatMessagesItem)), None)
    citations = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatCitationsItem)), None)
    scope = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ScopeSelectorItem)), None)

    assert isinstance(messages, ir.ChatMessagesItem)
    assert messages.source.path == ["chat", "messages"]
    assert isinstance(citations, ir.ChatCitationsItem)
    assert citations.source.path == ["chat", "citations"]
    assert isinstance(scope, ir.ScopeSelectorItem)
    assert scope.options_source.path == ["chat", "scope_options"]
    assert scope.active.path == ["chat", "scope_active"]


def test_rag_ui_research_defaults_include_on_send_when_binds_are_omitted() -> None:
    program = lower_ir_program(MINIMAL_RESEARCH_NO_BINDS_SOURCE)
    page = program.pages[0]
    composer = next((item for item in _walk_page_items(page.items) if isinstance(item, ir.ChatComposerItem)), None)
    assert isinstance(composer, ir.ChatComposerItem)
    assert composer.flow_name == "ask_question"


def _walk_page_items(items: list[ir.PageItem]):
    for item in items:
        yield item
        children = getattr(item, "children", None)
        if isinstance(children, list):
            yield from _walk_page_items(children)
        if isinstance(item, ir.SidebarLayout):
            yield from _walk_page_items(item.sidebar or [])
            yield from _walk_page_items(item.main or [])
        tabs = getattr(item, "tabs", None)
        if isinstance(tabs, list):
            for tab in tabs:
                yield from _walk_page_items(tab.children)

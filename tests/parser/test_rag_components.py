import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


SOURCE = '''flow "send":
  return "ok"

page "docs":
  citations from state.answer.citations
  trust_indicator from state.answer.trusted
  source_preview from state.preview
  scope_selector from state.documents active in state.active_docs
  chat:
    messages from is state.chat.messages
    citations from state.answer.citations
    trust_indicator from state.answer.trusted
    composer calls flow "send"
'''


def test_parse_rag_components_at_page_and_chat_levels() -> None:
    program = parse_program(SOURCE)
    page_items = program.pages[0].items
    assert any(isinstance(item, ast.CitationChipsItem) for item in page_items)
    assert any(isinstance(item, ast.TrustIndicatorItem) for item in page_items)
    assert any(isinstance(item, ast.SourcePreviewItem) for item in page_items)
    assert any(isinstance(item, ast.ScopeSelectorItem) for item in page_items)

    chat = next(item for item in page_items if isinstance(item, ast.ChatItem))
    assert any(isinstance(child, ast.CitationChipsItem) for child in chat.children)
    assert any(isinstance(child, ast.TrustIndicatorItem) for child in chat.children)


def test_parse_legacy_chat_citations_still_supported() -> None:
    source = '''page "home":
  chat:
    messages from is state.chat.messages
    citations from is state.chat.citations
'''
    program = parse_program(source)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    citations = next(child for child in chat.children if isinstance(child, ast.ChatCitationsItem))
    assert citations.source.path == ["chat", "citations"]


def test_scope_selector_requires_active_clause() -> None:
    source = '''page "docs":
  scope_selector from state.documents
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "active in state.<path>" in str(exc.value)


def test_source_preview_supports_literal_source_id() -> None:
    source = '''page "docs":
  source_preview from "doc-123"
'''
    program = parse_program(source)
    item = next(entry for entry in program.pages[0].items if isinstance(entry, ast.SourcePreviewItem))
    assert isinstance(item.source, ast.Literal)
    assert item.source.value == "doc-123"

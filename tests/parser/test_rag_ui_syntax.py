import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


def test_rag_ui_parses_block():
    source = '''page "RAG":
  rag_ui:
    base is "evidence"
    features: conversation, evidence
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
'''
    program = parse_program(source)
    rag = program.pages[0].items[0]
    assert isinstance(rag, ast.RagUIBlock)
    assert rag.base == "evidence"
    assert "conversation" in rag.features
    assert "evidence" in rag.features
    assert isinstance(rag.bindings, ast.RagUIBindings)
    assert isinstance(rag.bindings.messages, ast.StatePath)
    assert rag.bindings.on_send == "answer_question"
    assert isinstance(rag.bindings.citations, ast.StatePath)


def test_rag_ui_slots_parse():
    source = '''page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
    slots:
      sidebar:
        text is "Custom"
'''
    program = parse_program(source)
    rag = program.pages[0].items[0]
    assert "sidebar" in rag.slots
    assert isinstance(rag.slots["sidebar"][0], ast.TextItem)


def test_rag_ui_invalid_base():
    source = '''page "RAG":
  rag_ui:
    base is "unknown"
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      citations from is state.chat.citations
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "Unknown rag_ui base" in str(err.value)


def test_rag_ui_requires_binds():
    source = '''page "RAG":
  rag_ui:
    base is "assistant"
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "rag_ui requires a binds block" in str(err.value)

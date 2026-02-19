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


def test_rag_ui_allows_omitting_binds():
    source = '''page "RAG":
  rag_ui:
    base is "assistant"
'''
    program = parse_program(source)
    rag = program.pages[0].items[0]
    assert isinstance(rag, ast.RagUIBlock)
    assert rag.base == "assistant"
    assert rag.bindings is None


def test_rag_ui_research_allows_default_state_binds():
    source = '''page "RAG":
  rag_ui:
    base is "research"
    binds:
      on_send calls flow "answer_question"
'''
    program = parse_program(source)
    rag = program.pages[0].items[0]
    assert isinstance(rag, ast.RagUIBlock)
    assert rag.base == "research"
    assert isinstance(rag.bindings, ast.RagUIBindings)
    assert rag.bindings.on_send == "answer_question"
    assert rag.bindings.messages is None
    assert rag.bindings.citations is None
    assert rag.bindings.scope_options is None
    assert rag.bindings.scope_active is None


def test_rag_ui_research_allows_omitting_binds():
    source = '''page "RAG":
  rag_ui:
    base is "research"
'''
    program = parse_program(source)
    rag = program.pages[0].items[0]
    assert isinstance(rag, ast.RagUIBlock)
    assert rag.base == "research"
    assert rag.bindings is None


def test_rag_ui_parses_shell_bindings():
    source = '''page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      threads from is state.chat.threads
      active_thread when is state.chat.active_thread
      models from is state.chat.models
      active_models when is state.chat.active_models
      suggestions from is state.chat.suggestions
      composer_state when is state.chat.composer_state
'''
    program = parse_program(source)
    rag = program.pages[0].items[0]
    assert isinstance(rag.bindings, ast.RagUIBindings)
    assert isinstance(rag.bindings.threads, ast.StatePath)
    assert isinstance(rag.bindings.active_thread, ast.StatePath)
    assert isinstance(rag.bindings.models, ast.StatePath)
    assert isinstance(rag.bindings.active_models, ast.StatePath)
    assert isinstance(rag.bindings.suggestions, ast.StatePath)
    assert isinstance(rag.bindings.composer_state, ast.StatePath)


def test_rag_ui_threads_require_active_thread_binding():
    source = '''page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      threads from is state.chat.threads
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "threads requires active_thread" in str(err.value)


def test_rag_ui_models_require_active_models_binding():
    source = '''page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "answer_question"
      models from is state.chat.models
'''
    with pytest.raises(Namel3ssError) as err:
        parse_program(source)
    assert "models requires active_models" in str(err.value)

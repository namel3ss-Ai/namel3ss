import pytest

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from tests.conftest import parse_program


SOURCE = '''flow "send_message":
  return "ok"

page "home":
  chat:
    messages from is state.chat.messages
    composer calls flow "send_message"
    thinking when is state.chat.thinking
    citations from is state.chat.citations
    memory from is state.chat.memory lane is "team"
'''


def test_parse_chat_block():
    program = parse_program(SOURCE)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    assert len(chat.children) == 5
    messages = chat.children[0]
    composer = chat.children[1]
    thinking = chat.children[2]
    citations = chat.children[3]
    memory = chat.children[4]
    assert isinstance(messages, ast.ChatMessagesItem)
    assert messages.source.path == ["chat", "messages"]
    assert isinstance(composer, ast.ChatComposerItem)
    assert composer.flow_name == "send_message"
    assert isinstance(thinking, ast.ChatThinkingItem)
    assert thinking.when.path == ["chat", "thinking"]
    assert isinstance(citations, ast.ChatCitationsItem)
    assert citations.source.path == ["chat", "citations"]
    assert isinstance(memory, ast.ChatMemoryItem)
    assert memory.source.path == ["chat", "memory"]
    assert memory.lane == "team"


def test_parse_chat_composer_structured_fields():
    source = '''flow "ask_flow":
  return "ok"

page "home":
  chat:
    composer sends to flow "ask_flow"
      send category as text
          language as text
'''
    program = parse_program(source)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    composer = next(child for child in chat.children if isinstance(child, ast.ChatComposerItem))
    assert composer.flow_name == "ask_flow"
    assert [field.name for field in composer.fields] == ["category", "language"]
    assert [field.type_name for field in composer.fields] == ["text", "text"]


def test_chat_elements_outside_block_error():
    source = '''page "home":
  messages from is state.chat.messages
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "chat elements must be inside" in str(exc.value).lower()


def test_chat_memory_lane_must_be_known():
    source = '''page "home":
  chat:
    memory from is state.chat.memory lane is "org"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "lane must be" in str(exc.value).lower()


def test_parse_chat_block_with_enhanced_options():
    source = '''flow "send_message":
  return "ok"

page "home":
  chat:
    style is "plain"
    show_avatars is true
    group_messages is false
    actions are [copy, expand, view_sources, copy]
    streaming is true
    attachments are true
    messages from is state.chat.messages
    composer calls flow "send_message"
'''
    program = parse_program(source)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    assert chat.style == "plain"
    assert chat.show_avatars is True
    assert chat.group_messages is False
    assert chat.actions == ["copy", "expand", "view_sources"]
    assert chat.streaming is True
    assert chat.attachments is True


def test_parse_chat_block_with_composer_attach_upload():
    source = '''flow "send_message":
  return "ok"

page "home":
  chat:
    attachments are true
    composer_attach_upload is "question_files"
    messages from is state.chat.messages
    composer calls flow "send_message"
'''
    program = parse_program(source)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    assert chat.attachments is True
    assert chat.composer_attach_upload == "question_files"


def test_parse_thinking_clause_without_is():
    source = '''flow "send_message":
  return "ok"

page "home":
  chat:
    messages from is state.chat.messages
    composer calls flow "send_message"
    thinking when state.chat.thinking
'''
    program = parse_program(source)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    thinking = next(child for child in chat.children if isinstance(child, ast.ChatThinkingItem))
    assert thinking.when.path == ["chat", "thinking"]


def test_chat_option_duplicate_error():
    source = '''flow "send_message":
  return "ok"

page "home":
  chat:
    style is "plain"
    style is "bubbles"
    messages from is state.chat.messages
    composer calls flow "send_message"
'''
    with pytest.raises(Namel3ssError) as exc:
        parse_program(source)
    assert "declared more than once" in str(exc.value).lower()


def test_chat_option_allows_custom_actions():
    source = '''flow "send_message":
  return "ok"

page "home":
  chat:
    actions are [copy, pin, open_in_drawer, pin]
    messages from is state.chat.messages
    composer calls flow "send_message"
'''
    program = parse_program(source)
    chat = next(item for item in program.pages[0].items if isinstance(item, ast.ChatItem))
    assert chat.actions == ["copy", "pin", "open_in_drawer"]

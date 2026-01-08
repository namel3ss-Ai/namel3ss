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

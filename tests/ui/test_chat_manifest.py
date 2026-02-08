import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


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


STATE = {
    "chat": {
        "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello", "created": "now"},
        ],
        "thinking": True,
        "citations": [
            {"title": "Spec", "url": "https://example.com", "snippet": "Details"},
            {"title": "Note", "source_id": "ref-1"},
        ],
        "memory": [
            {"kind": "fact", "text": "Likes green"},
            {"kind": "decision", "text": "Prefers email"},
        ],
    }
}

STRUCTURED_SOURCE = '''contract flow "ask_flow":
  input:
    message is text
    category is text
    language is text
  output:
    result is text

flow "ask_flow":
  return "ok"

page "home":
  chat:
    composer sends to flow "ask_flow"
      send category as text
          language as text
'''

ENHANCED_SOURCE = '''spec is "1.0"

capabilities:
  streaming

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "ask_flow":
  ask ai "assistant" with stream: true and input: "hello" as reply
  return reply

page "home":
  chat:
    style is "bubbles"
    show_avatars is true
    group_messages is true
    actions are [copy, expand, view_sources]
    streaming is true
    attachments are true
    messages from is state.chat.messages
    composer calls flow "ask_flow"
    thinking when state.chat.thinking
'''

ENHANCED_STATE = {
    "chat": {
        "messages": [
            {"role": "user", "content": "Hello"},
            {
                "role": "assistant",
                "content": "First answer",
                "citations": [{"title": "Doc", "source_id": "doc:1"}],
                "actions": ["copy"],
            },
            {
                "role": "assistant",
                "content": "Second answer with files",
                "attachments": [{"type": "file", "name": "spec.pdf", "url": "https://example.com/spec.pdf"}],
                "tokens": ["Second ", "answer ", "with ", "files"],
            },
        ],
        "thinking": True,
    }
}


def _chat_children(manifest: dict) -> dict:
    chat = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chat")
    return {child["type"]: child for child in chat["children"]}


def _chat_element(manifest: dict) -> dict:
    return next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chat")


def test_chat_manifest_includes_children_and_actions():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state=STATE)
    children = _chat_children(manifest)

    messages = children["messages"]
    assert [entry["role"] for entry in messages["messages"]] == ["user", "assistant"]
    assert [entry["content"] for entry in messages["messages"]] == ["Hi", "Hello"]
    assert messages["messages"][0]["group_start"] is True
    assert messages["messages"][1]["group_start"] is True
    assert messages["source"] == "state.chat.messages"

    thinking = children["thinking"]
    assert thinking["active"] is True
    assert thinking["when"] == "state.chat.thinking"

    citations = children["citations"]
    assert citations["citations"] == STATE["chat"]["citations"]

    memory = children["memory"]
    assert memory["items"] == STATE["chat"]["memory"]
    assert memory["lane"] == "team"

    composer = children["composer"]
    action_id = composer["action_id"]
    assert action_id in manifest["actions"]
    assert manifest["actions"][action_id]["type"] == "call_flow"
    assert manifest["actions"][action_id]["flow"] == "send_message"


def test_chat_manifest_is_deterministic():
    program = lower_ir_program(SOURCE)
    manifest_one = build_manifest(program, state=STATE)
    manifest_two = build_manifest(program, state=STATE)
    assert manifest_one == manifest_two


def test_chat_manifest_structured_fields_and_action_ids():
    program = lower_ir_program(STRUCTURED_SOURCE)
    manifest = build_manifest(program, state=STATE)
    children = _chat_children(manifest)
    composer = children["composer"]
    action_id = composer["action_id"]
    assert action_id == "page.home.composer.0.0.composer"
    fields = composer["fields"]
    assert fields == [
        {"name": "message", "type": "text"},
        {"name": "category", "type": "text"},
        {"name": "language", "type": "text"},
    ]
    assert manifest["actions"][action_id]["fields"] == fields
    manifest_second = build_manifest(program, state=STATE)
    assert manifest == manifest_second


def test_chat_manifest_invalid_messages_error():
    program = lower_ir_program(SOURCE)
    bad_state = {"chat": {"messages": {"role": "user"}}}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state=bad_state)
    assert "messages must be a list" in str(exc.value).lower()


def test_chat_manifest_invalid_citation_error():
    program = lower_ir_program(SOURCE)
    bad_state = {"chat": {"messages": [], "thinking": False, "citations": [{"title": "Spec"}], "memory": []}}
    with pytest.raises(Namel3ssError) as exc:
        build_manifest(program, state=bad_state)
    assert "citation 0 must include url or source_id" in str(exc.value).lower()


def test_chat_manifest_sets_enhanced_chat_defaults():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state=STATE)
    chat = _chat_element(manifest)
    assert chat["style"] == "bubbles"
    assert chat["show_avatars"] is False
    assert chat["group_messages"] is True
    assert chat["streaming"] is False
    assert chat["attachments"] is False
    assert chat["actions"] == []


def test_chat_manifest_applies_enhanced_configuration_and_grouping():
    program = lower_ir_program(ENHANCED_SOURCE)
    manifest = build_manifest(program, state=ENHANCED_STATE)
    chat = _chat_element(manifest)
    assert chat["style"] == "bubbles"
    assert chat["show_avatars"] is True
    assert chat["group_messages"] is True
    assert chat["streaming"] is True
    assert chat["attachments"] is True
    assert chat["actions"] == ["copy", "expand", "view_sources"]

    children = _chat_children(manifest)
    thinking = children["thinking"]
    assert thinking["active"] is True
    assert thinking["debug_only"] is False
    assert thinking["user_visible"] is True

    messages = children["messages"]["messages"]
    assert [entry["group_start"] for entry in messages] == [True, True, False]
    assert messages[0]["actions"] == ["copy", "expand", "view_sources"]
    assert messages[1]["actions"] == ["copy"]
    assert messages[1]["citations"][0]["index"] == 1
    assert messages[2]["streaming"] is True
    assert messages[2]["attachments"][0]["type"] == "file"


def test_chat_manifest_enhanced_is_deterministic():
    program = lower_ir_program(ENHANCED_SOURCE)
    manifest_one = build_manifest(program, state=ENHANCED_STATE)
    manifest_two = build_manifest(program, state=ENHANCED_STATE)
    assert manifest_one == manifest_two

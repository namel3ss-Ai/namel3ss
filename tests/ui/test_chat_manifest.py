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


def _chat_children(manifest: dict) -> dict:
    chat = next(el for el in manifest["pages"][0]["elements"] if el["type"] == "chat")
    return {child["type"]: child for child in chat["children"]}


def test_chat_manifest_includes_children_and_actions():
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state=STATE)
    children = _chat_children(manifest)

    messages = children["messages"]
    assert messages["messages"] == STATE["chat"]["messages"]
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

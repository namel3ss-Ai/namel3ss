from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''capabilities:
  ui_rag

flow "send":
  return "ok"

page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "send"
      threads from is state.chat.threads
      active_thread when is state.chat.active_thread
      models from is state.chat.models
      active_models when is state.chat.active_models
      composer_state when is state.chat.composer_state
'''


SOURCE_WITH_SUGGESTIONS = '''capabilities:
  ui_rag

flow "send":
  return "ok"

page "RAG":
  rag_ui:
    binds:
      messages from is state.chat.messages
      on_send calls flow "send"
      suggestions from is state.chat.suggestions
'''


STATE = {
    "chat": {
        "messages": [{"id": "message.1", "role": "user", "content": "Hello"}],
        "threads": [{"id": "thread.main", "name": "Main"}],
        "active_thread": ["thread.main"],
        "models": [{"id": "model.alpha", "name": "Alpha"}],
        "active_models": ["model.alpha"],
        "composer_state": {
            "attachments": ["upload.a"],
            "draft": "Draft question",
            "tools": ["web.lookup"],
            "web_search": True,
        },
    }
}


def test_rag_shell_bindings_emit_chat_selector_actions() -> None:
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state=STATE)
    elements = list(_walk_page_elements(manifest["pages"][0]))
    selectors = [entry for entry in elements if entry.get("type") == "scope_selector"]
    by_title = {entry.get("title"): entry for entry in selectors}

    thread_selector = by_title["Threads"]
    thread_action = manifest["actions"][thread_selector["action_id"]]
    assert thread_action["type"] == "chat.thread.select"
    assert thread_selector["selection"] == "single"
    assert thread_selector["action_type"] == "chat.thread.select"

    model_selector = by_title["Models"]
    model_action = manifest["actions"][model_selector["action_id"]]
    assert model_action["type"] == "chat.model.select"
    assert model_selector["selection"] == "multi"
    assert model_selector["action_type"] == "chat.model.select"

    messages = next((entry for entry in elements if entry.get("type") == "messages"), None)
    assert isinstance(messages, dict)
    assert messages["messages"][0]["id"] == "message.1"
    branch_action = manifest["actions"][messages["branch_action_id"]]
    regenerate_action = manifest["actions"][messages["regenerate_action_id"]]
    cancel_action = manifest["actions"][messages["stream_cancel_action_id"]]
    assert branch_action["type"] == "chat.branch.select"
    assert branch_action["target_state"] == "state.chat.messages_graph.active_message_id"
    assert regenerate_action["type"] == "chat.message.regenerate"
    assert regenerate_action["target_state"] == "state.chat.messages_graph.active_message_id"
    assert cancel_action["type"] == "chat.stream.cancel"
    assert cancel_action["target_state"] == "state.chat.stream_state.cancel_requested"

    composer = next((entry for entry in elements if entry.get("type") == "composer"), None)
    assert isinstance(composer, dict)
    composer_action = manifest["actions"][composer["action_id"]]
    assert composer["action_type"] == "chat.message.send"
    assert composer_action["type"] == "chat.message.send"
    assert composer["composer_state_source"] == "state.chat.composer_state"
    assert composer["composer_state"] == {
        "attachments": ["upload.a"],
        "draft": "Draft question",
        "tools": ["web.lookup"],
        "web_search": True,
    }


def test_rag_shell_includes_suggestion_board_binding() -> None:
    program = lower_ir_program(SOURCE_WITH_SUGGESTIONS)
    state = {
        "chat": {
            "messages": [],
            "suggestions": [{"prompt": "Summarize this", "title": "Summarize"}],
        }
    }
    manifest = build_manifest(program, state=state)
    elements = list(_walk_page_elements(manifest["pages"][0]))
    suggestions = [entry for entry in elements if entry.get("type") == "list" and entry.get("source") == "state.chat.suggestions"]
    assert suggestions


def _walk_page_elements(page: dict):
    layout = page.get("layout")
    if isinstance(layout, dict):
        for slot in ("header", "sidebar_left", "main", "drawer_right", "footer"):
            for element in _walk_elements(layout.get(slot, [])):
                yield element
        return
    for element in _walk_elements(page.get("elements", [])):
        yield element


def _walk_elements(elements: list[dict]):
    for element in elements:
        if not isinstance(element, dict):
            continue
        yield element
        children = element.get("children")
        if isinstance(children, list):
            yield from _walk_elements(children)
        sidebar = element.get("sidebar")
        if isinstance(sidebar, list):
            yield from _walk_elements(sidebar)
        main = element.get("main")
        if isinstance(main, list):
            yield from _walk_elements(main)

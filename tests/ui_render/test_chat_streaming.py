from pathlib import Path


def test_chat_streaming_start_middle_end_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for marker in [
        'contentNode.dataset.streamPhase = "thinking"',
        'contentNode.dataset.streamPhase = "streaming"',
        'contentNode.dataset.streamPhase = "complete"',
        "ui-chat-stream-thinking",
        "revealMessageCitations",
        "setInterval",
    ]:
        assert marker in js


def test_chat_streaming_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/chat.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-chat-content[data-stream-phase=\"thinking\"]",
        ".ui-chat-stream-thinking",
        ".ui-chat-attachments[data-stream-visible=\"false\"]",
    ]:
        assert selector in css


def test_chat_layout_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/chat.css").read_text(encoding="utf-8")
    for marker in [
        ".ui-chat {",
        ".ui-chat-messages {",
        ".ui-chat-composer {",
        "grid-template-columns: minmax(0, 1fr) auto;",
    ]:
        assert marker in css


def test_chat_keyboard_send_and_newline_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    assert "event.shiftKey" in js
    assert "form.requestSubmit" in js
    assert 'name === "message"' in js

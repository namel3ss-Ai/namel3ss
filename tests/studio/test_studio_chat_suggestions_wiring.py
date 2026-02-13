from pathlib import Path


def test_collection_renderer_wires_chat_suggestion_click_to_send_action() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_collections.js").read_text(encoding="utf-8")
    for expected in [
        'source !== "state.chat.suggestions"',
        'entry.type === "chat.message.send"',
        "suggestionMessageFromRow(",
        'handleAction(suggestionAction, { message: message, source: "suggestion" }, item)',
    ]:
        assert expected in js

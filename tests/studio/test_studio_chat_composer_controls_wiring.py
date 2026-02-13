from pathlib import Path


def test_chat_renderer_wires_advanced_composer_controls() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for expected in [
        "normalizeComposerState(",
        "buildComposerAdvancedControls(",
        "buildComposerListEditor(",
        "payload.attachments = advancedPayload.attachments",
        "payload.tools = advancedPayload.tools",
        "payload.web_search = advancedPayload.web_search",
        "Web search",
    ]:
        assert expected in js

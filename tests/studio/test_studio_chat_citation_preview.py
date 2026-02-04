from pathlib import Path


def test_chat_citation_preview_wiring() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    assert "openCitationPreview" in js
    assert "ui-citation-preview" in js
    assert "Open page" in js
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    assert ".ui-citation-preview-frame" in css
    assert ".ui-chat-citation-actions" in css

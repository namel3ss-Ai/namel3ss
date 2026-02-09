from pathlib import Path


def test_empty_loading_error_state_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for marker in [
        "renderNoSourcesPanel",
        "Upload document",
        "Searching sources...",
        "ui-chat-error-surface",
    ]:
        assert marker in js


def test_empty_state_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/empty_states.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-empty-sources-panel",
        ".ui-empty-sources-actions",
        ".ui-chat-error-surface",
    ]:
        assert selector in css


def test_chat_and_empty_state_styles_are_linked() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/styles/chat.css" in html
    assert "/styles/empty_states.css" in html

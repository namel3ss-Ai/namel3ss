from pathlib import Path


def test_chat_renderer_supports_clickable_inline_citations_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for marker in [
        "renderInlineCitationText",
        "resolveInlineCitationEntry",
        "ui-chat-inline-citation",
        "openCitationPreview(citationEntry, button, citations)",
    ]:
        assert marker in js


def test_chat_inline_citation_styles_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/chat.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-chat-inline-citation",
        ".ui-chat-inline-citation:hover",
        ".ui-chat-inline-citation:focus-visible",
    ]:
        assert selector in css

from pathlib import Path


def test_pdf_preview_renderer_wiring() -> None:
    index_html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_pdf_preview.js" in index_html

    helper_js = Path("src/namel3ss/studio/web/ui_renderer_pdf_preview.js").read_text(encoding="utf-8")
    assert "buildCitationDeepLinkQuery" in helper_js
    assert "applyCitationDeepLinkState" in helper_js
    assert "buildPdfPreviewRequestUrl" in helper_js
    assert "citationColorIndex" in helper_js

    chat_js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    assert "buildPdfPreviewRequestUrl" in chat_js
    assert "applyCitationDeepLinkState" in chat_js
    assert "ui-citation-highlight-" in chat_js

    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    assert ".ui-citation-highlight-0" in css
    assert ".ui-citation-highlight-7" in css

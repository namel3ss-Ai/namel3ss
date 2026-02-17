from pathlib import Path


def test_chat_preview_resolver_supports_preview_url_and_deep_link_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for marker in [
        "parsePreviewTargetFromUrl",
        "parsePreviewTargetFromDeepLink",
        "looksLikeDocumentId",
        "textValue(entry.preview_url)",
        "new URLSearchParams(query)",
        "params.get(\"n3_chunk\")",
        "params.get(\"chunk_id\")",
        "params.get(\"doc\")",
        "params.get(\"page\")",
    ]:
        assert marker in js


def test_chat_preview_selection_uses_resolved_citation_id_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    assert "target.citationId" in js


def test_chat_preview_unavailable_uses_requested_page_and_pdf_fallback_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for marker in [
        "docMeta.requested_page",
        "payload.pdf_url",
        "buildCitationPdfPreviewUrl",
        "preview.frame.src = buildCitationPdfPreviewUrl",
        "params.set(\"search\"",
    ]:
        assert marker in js

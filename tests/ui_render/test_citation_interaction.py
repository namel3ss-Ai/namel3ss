from pathlib import Path


def test_citation_chip_opens_drawer_and_selects_source_contract() -> None:
    rag = Path("src/namel3ss/studio/web/ui_renderer_rag.js").read_text(encoding="utf-8")
    assert "openCitation(entry, button, citations)" in rag
    assert "focusCitationInDrawer" in rag

    chat = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    for marker in [
        "openCitationPreview(entry, opener, citationSet)",
        'setCitationPreviewTab("sources")',
        "renderPreviewSources",
        "selectPreviewCitation(index, { openPreviewTab: true })",
    ]:
        assert marker in chat


def test_citation_list_item_routes_to_preview_contract() -> None:
    collections = Path("src/namel3ss/studio/web/ui_renderer_collections.js").read_text(encoding="utf-8")
    assert "ui-list-citation-item" in collections
    assert "focusDrawerPreviewForCitation" in collections

    drawer_css = Path("src/namel3ss/studio/web/styles/drawer.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-citation-preview-tab.active",
        ".ui-citation-preview-source.active",
        ".ui-citation-preview-sources",
    ]:
        assert selector in drawer_css

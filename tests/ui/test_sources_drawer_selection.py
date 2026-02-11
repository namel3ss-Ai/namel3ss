from __future__ import annotations

from pathlib import Path


def test_sources_drawer_uses_stable_citation_ids_for_selection() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    collections = Path("src/namel3ss/studio/web/ui_renderer_collections.js").read_text(encoding="utf-8")
    rag = Path("src/namel3ss/studio/web/ui_renderer_rag.js").read_text(encoding="utf-8")
    chat = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")

    assert "function selectCitationId" in renderer
    assert "focusCitationInDrawer" in renderer
    assert "collectionRender.selectCitationId" in renderer
    assert "querySelectorAll(\"[data-citation-id]\")" in renderer

    assert "item.dataset.citationId = citationEntry.citation_id" in collections
    assert "root.selectCitationId(citationEntry.citation_id)" in collections

    assert "button.dataset.citationId = entry.citation_id" in rag
    assert "root.selectCitationId(entry.citation_id)" in rag

    assert "item.dataset.citationId = entry.citation_id" in chat


def test_sources_drawer_selection_styles_exist() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    assert ".ui-citation-chip.selected" in css
    assert ".ui-citation-preview-source.selected" in css
    assert ".ui-list-citation-item.selected" in css


from pathlib import Path


def test_rag_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_rag.js" in html

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "citation_chips"' in renderer
    assert 'el.type === "source_preview"' in renderer
    assert 'el.type === "trust_indicator"' in renderer
    assert 'el.type === "scope_selector"' in renderer

    rag = Path("src/namel3ss/studio/web/ui_renderer_rag.js").read_text(encoding="utf-8")
    assert "renderCitationChipsElement" in rag
    assert "renderSourcePreviewElement" in rag
    assert "renderTrustIndicatorElement" in rag
    assert "renderScopeSelectorElement" in rag
    assert "root.openCitationPreview" in Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")


def test_rag_component_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-citation-chips",
        ".ui-citation-chip",
        ".ui-source-preview",
        ".ui-trust-indicator",
        ".ui-scope-selector",
        ".ui-scope-option.active",
    ]:
        assert selector in css

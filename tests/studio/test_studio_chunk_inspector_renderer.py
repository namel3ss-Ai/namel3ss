from __future__ import annotations

from pathlib import Path


def test_chunk_inspector_renderer_script_and_ui_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_chunk_inspection.js" in html

    ui_renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "chunk_inspector"' in ui_renderer
    assert "renderChunkInspectorElement" in ui_renderer

    chunk_renderer = Path("src/namel3ss/studio/web/ui_renderer_chunk_inspection.js").read_text(encoding="utf-8")
    assert "renderChunkInspectorElement" in chunk_renderer
    assert "/api/chunks/inspection" in chunk_renderer
    assert "openChunkPreview" in chunk_renderer


def test_chunk_inspector_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-chunk-inspector",
        ".ui-chunk-inspector-table",
        ".ui-chunk-inspector-pages",
        ".ui-chunk-inspector-status",
    ]:
        assert selector in css

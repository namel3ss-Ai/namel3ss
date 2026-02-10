from __future__ import annotations

from pathlib import Path


def test_ga_component_files_exist_with_basic_structure() -> None:
    root = Path("src/namel3ss/studio/web/components")
    required = (
        "Sidebar.vue",
        "Drawer.vue",
        "StickyBar.vue",
        "ScrollArea.vue",
        "MultiPane.vue",
        "ChatThread.vue",
        "CitationPanel.vue",
        "DocumentLibrary.vue",
        "IngestionProgress.vue",
        "ExplainMode.vue",
        "PluginManager.vue",
        "LocaleSelector.vue",
        "ThemePreview.vue",
    )
    for filename in required:
        path = root / filename
        assert path.exists(), f"missing component: {filename}"
        text = path.read_text(encoding="utf-8")
        assert "<template>" in text
        assert "<script>" in text
        assert "<style" in text


def test_studio_renderer_avoids_debug_noise_in_non_studio_paths() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert "n3:plugin-component" in js
    assert "ensurePluginAssets" in js
    assert "console.debug" not in js

import json
from pathlib import Path


def test_capability_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/renderer_registry.js" in html
    manifest = json.loads(Path("src/namel3ss/studio/web/renderer_manifest.json").read_text(encoding="utf-8"))
    renderer_ids = [entry.get("renderer_id") for entry in manifest.get("renderers", [])]
    # Deviation from legacy tag checks: renderers are loaded through renderer_registry.js.
    assert "capabilities" in renderer_ids

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "capabilities"' in renderer
    assert "renderCapabilitiesElement" in renderer

    source = Path("src/namel3ss/studio/web/ui_renderer_capabilities.js").read_text(encoding="utf-8")
    assert "renderCapabilitiesElement" in source
    assert "Capability Packs" in source
    assert "No capability packs enabled." in source


def test_capability_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-capabilities",
        ".ui-capabilities-list",
        ".ui-capabilities-item",
        ".ui-capabilities-version",
        ".ui-capabilities-row",
    ]:
        assert selector in css

import json
from pathlib import Path


def test_drawer_focus_trap_and_tab_control_contract() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    for marker in [
        'entry.type === "drawer"',
        "matchMedia(\"(max-width: 960px)\")",
        "n3SetActiveTabByLabel",
        "focusCitationInDrawer",
        "focusDrawerPreviewForCitation",
    ]:
        assert marker in renderer


def test_drawer_transition_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/drawer.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-overlay.hidden",
        ".ui-overlay.ui-drawer .ui-overlay-panel",
        ".ui-overlay.ui-drawer.hidden .ui-overlay-panel",
    ]:
        assert selector in css


def test_runtime_and_studio_load_rag_drawer_assets() -> None:
    manifest = json.loads(Path("src/namel3ss/studio/web/renderer_manifest.json").read_text(encoding="utf-8"))
    renderer_ids = [entry.get("renderer_id") for entry in manifest.get("renderers", [])]
    # Deviation from legacy tag checks: renderers are loaded through renderer_registry.js.
    assert "rag" in renderer_ids
    for path in [
        "src/namel3ss/studio/web/index.html",
        "src/namel3ss/runtime/web/dev.html",
        "src/namel3ss/runtime/web/preview.html",
        "src/namel3ss/runtime/web/prod.html",
    ]:
        html = Path(path).read_text(encoding="utf-8")
        assert "/renderer_registry.js" in html
        assert "/styles/drawer.css" in html

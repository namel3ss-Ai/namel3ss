import json
from pathlib import Path


def test_runtime_error_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/renderer_registry.js" in html
    manifest = json.loads(Path("src/namel3ss/studio/web/renderer_manifest.json").read_text(encoding="utf-8"))
    renderer_ids = [entry.get("renderer_id") for entry in manifest.get("renderers", [])]
    # Deviation from legacy tag checks: renderers are loaded through renderer_registry.js.
    assert "runtime_error" in renderer_ids

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "runtime_error"' in renderer
    assert "renderRuntimeErrorElement" in renderer

    runtime_renderer = Path("src/namel3ss/studio/web/ui_renderer_runtime_error.js").read_text(encoding="utf-8")
    assert "renderRuntimeErrorElement" in runtime_renderer
    assert "ui-runtime-error" in runtime_renderer
    assert "Additional diagnostics" in runtime_renderer


def test_runtime_error_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-runtime-error",
        ".ui-runtime-error-badge",
        ".ui-runtime-error-message",
        ".ui-runtime-error-hint",
        ".ui-runtime-error-diagnostic",
    ]:
        assert selector in css


def test_runtime_error_renderer_snapshot_strings() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer_runtime_error.js").read_text(encoding="utf-8")
    assert "Runtime warning" in renderer
    assert "Runtime error" in renderer
    assert "origin:" in renderer

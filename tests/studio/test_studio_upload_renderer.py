import json
from pathlib import Path


def test_upload_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/renderer_registry.js" in html
    manifest = json.loads(Path("src/namel3ss/studio/web/renderer_manifest.json").read_text(encoding="utf-8"))
    renderer_ids = [entry.get("renderer_id") for entry in manifest.get("renderers", [])]
    # Deviation from legacy tag checks: renderers are loaded through renderer_registry.js.
    assert "upload" in renderer_ids

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "upload"' in renderer
    assert "renderUploadElement" in renderer

    upload_renderer = Path("src/namel3ss/studio/web/ui_renderer_upload.js").read_text(encoding="utf-8")
    assert "renderUploadElement" in upload_renderer
    assert "/api/upload?name=" in upload_renderer
    assert "upload_clear" in upload_renderer


def test_upload_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-upload",
        ".ui-upload-status",
        ".ui-upload-file-item",
        ".ui-upload-preview-item",
    ]:
        assert selector in css

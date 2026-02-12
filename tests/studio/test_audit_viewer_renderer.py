from pathlib import Path


def test_audit_viewer_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/renderer_registry.js" in html
    assert "/ui_renderer_audit_viewer.js" not in html

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "audit_viewer"' in renderer
    assert "renderAuditViewerElement" in renderer

    audit_renderer = Path("src/namel3ss/studio/web/ui_renderer_audit_viewer.js").read_text(encoding="utf-8")
    assert "renderAuditViewerElement" in audit_renderer
    assert "Run History / Audit Viewer" in audit_renderer
    assert "Replay this run:" in audit_renderer


def test_audit_viewer_renderer_snapshot_strings() -> None:
    source = Path("src/namel3ss/studio/web/ui_renderer_audit_viewer.js").read_text(encoding="utf-8")
    for token in [
        "Deterministic checksums",
        "Inspect run artifact",
        "ui-audit-viewer-json",
    ]:
        assert token in source


def test_audit_viewer_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-audit-viewer",
        ".ui-audit-viewer-replay",
        ".ui-audit-viewer-checksum-list",
        ".ui-audit-viewer-json",
    ]:
        assert selector in css

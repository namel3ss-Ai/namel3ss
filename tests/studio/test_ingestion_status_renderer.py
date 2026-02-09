from pathlib import Path


def test_ingestion_status_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_ingestion_status.js" in html

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "ingestion_status"' in renderer
    assert "renderIngestionStatusElement" in renderer

    ingestion_renderer = Path("src/namel3ss/studio/web/ui_renderer_ingestion_status.js").read_text(encoding="utf-8")
    assert "renderIngestionStatusElement" in ingestion_renderer
    assert "ui-ingestion-status" in ingestion_renderer
    assert "Fallback used:" in ingestion_renderer


def test_ingestion_status_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-ingestion-status",
        ".ui-ingestion-status-badge",
        ".ui-ingestion-status-reason",
        ".ui-ingestion-status-code",
        ".ui-ingestion-status-remediation",
    ]:
        assert selector in css


def test_ingestion_status_renderer_snapshot_strings() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer_ingestion_status.js").read_text(encoding="utf-8")
    assert "Ingestion ${status}" in renderer
    assert "No ingestion warnings." in renderer
    assert "ui-ingestion-status-empty" in renderer

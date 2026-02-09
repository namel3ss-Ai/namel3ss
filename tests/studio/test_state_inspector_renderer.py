from pathlib import Path


def test_state_inspector_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_state_viewer.js" in html

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "state_inspector"' in renderer
    assert "renderStateInspectorElement" in renderer


def test_state_inspector_renderer_snapshot_strings() -> None:
    source = Path("src/namel3ss/studio/web/ui_renderer_state_viewer.js").read_text(encoding="utf-8")
    for token in [
        "State Inspector",
        "Pending Migrations",
        "Persisted state snapshot",
        "state_schema@1",
    ]:
        assert token in source


def test_state_inspector_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-state-inspector",
        ".ui-state-inspector-title",
        ".ui-state-inspector-row",
        ".ui-state-inspector-json",
    ]:
        assert selector in css

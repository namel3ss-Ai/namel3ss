from pathlib import Path


def test_studio_diagnostics_panel_script_exists():
    js = Path("src/namel3ss/studio/web/studio/diagnostics.js").read_text(encoding="utf-8")
    assert "renderDiagnostics" in js
    assert "No diagnostics pages or blocks declared." in js


def test_ui_renderer_renders_diagnostics_toggle():
    js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert "Show Explain" in js
    assert "n3-diagnostics" in js


def test_diagnostics_styles_follow_theme_tokens():
    css = Path("src/namel3ss/studio/web/studio_ui_integration.css").read_text(encoding="utf-8")
    assert "n3-diagnostics" in css
    assert "var(--n3-secondary-color)" in css
    assert "var(--n3-background-color)" in css

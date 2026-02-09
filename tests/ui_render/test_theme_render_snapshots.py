from pathlib import Path


def test_theme_renderer_supports_settings_page() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "theme.settings_page"' in renderer


def test_theme_tokens_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/theme.css").read_text(encoding="utf-8")
    for selector in [
        ".n3-size-compact",
        ".n3-radius-md",
        ".n3-density-tight",
        ".n3-font-sm",
        ".n3-theme-settings",
    ]:
        assert selector in css


def test_theme_tokens_css_is_linked() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/styles/theme.css" in html
    runtime = Path("src/namel3ss/runtime/web/prod.html").read_text(encoding="utf-8")
    assert "/styles/theme.css" in runtime

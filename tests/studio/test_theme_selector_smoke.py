from pathlib import Path


def test_theme_selector_present():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert 'id="themeSelect"' in html
    assert "Seed" in html  # ensure topbar controls intact
    assert "theme_tokens.js" in html
    assert "theme_tokens.css" in html
    assert "theme_runtime.js" in html
    assert "theme_preference.js" in html

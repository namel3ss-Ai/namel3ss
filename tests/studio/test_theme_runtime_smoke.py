from pathlib import Path


def test_runtime_theme_hooks_present():
    content = Path("src/namel3ss/studio/web/app.js").read_text(encoding="utf-8")
    assert "theme.current" in content
    assert "runtimeTheme" in content

from pathlib import Path


def _app_bundle():
    app_root = Path("src/namel3ss/studio/web/app")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(app_root.rglob("*.js")))


def test_runtime_theme_hooks_present():
    content = _app_bundle()
    assert "theme.current" in content
    assert "runtimeTheme" in content

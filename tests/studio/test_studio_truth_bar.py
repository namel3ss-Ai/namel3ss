from pathlib import Path


def _app_bundle():
    app_root = Path("src/namel3ss/studio/web/app")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(app_root.rglob("*.js")))


def test_truth_bar_present():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert 'id="truthBar"' in html
    assert 'id="truthStore"' in html
    assert 'id="truthRuntime"' in html
    assert 'id="truthOverride"' in html
    assert "trust_bar.js" in html
    assert "trace_utils.js" in html


def test_reset_confirmation_copy_present():
    js = _app_bundle()
    assert "Reset will clear state" in js
    assert "Reset will clear persisted records/state" in js


def test_theme_labels_present():
    trust_js = Path("src/namel3ss/studio/web/trust_bar.js").read_text(encoding="utf-8")
    assert "Store:" in trust_js
    assert "Theme (preview only)" in trust_js
    assert "Theme (engine, Studio local preference)" in trust_js
    assert "Preview override: ON" in trust_js

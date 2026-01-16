from pathlib import Path


def test_dev_html_includes_overlay_and_status() -> None:
    html = Path("src/namel3ss/runtime/web/dev.html").read_text(encoding="utf-8")
    assert 'id="devOverlay"' in html
    assert 'id="runtimeStatus"' in html
    assert 'mode: "dev"' in html
    assert "/runtime.js" in html


def test_preview_html_excludes_overlay_and_status() -> None:
    html = Path("src/namel3ss/runtime/web/preview.html").read_text(encoding="utf-8")
    assert 'id="devOverlay"' not in html
    assert "runtimeStatus" not in html
    assert 'mode: "preview"' in html


def test_prod_html_excludes_overlay_status_and_badge() -> None:
    html = Path("src/namel3ss/runtime/web/prod.html").read_text(encoding="utf-8")
    assert 'id="devOverlay"' not in html
    assert "runtimeStatus" not in html
    assert "runtime-badge" not in html
    assert 'mode: "preview"' in html

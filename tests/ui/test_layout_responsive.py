from pathlib import Path


def test_layout_css_contains_slot_regions_and_sticky_footer():
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".n3-layout-root",
        ".n3-layout-header",
        ".n3-layout-body",
        ".n3-layout-sidebar",
        ".n3-layout-main",
        ".n3-layout-drawer",
        ".n3-layout-footer",
    ]:
        assert selector in css
    assert ".n3-layout-footer" in css and "position: sticky" in css


def test_layout_css_has_deterministic_mobile_breakpoint():
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    assert "@media (max-width: 960px)" in css
    assert ".n3-layout-sidebar-toggle" in css
    assert ".n3-layout-sidebar-drawer.open" in css


def test_ui_renderer_supports_layout_slots_and_mobile_sidebar_drawer():
    js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert '"sidebar_left"' in js
    assert '"drawer_right"' in js
    assert "normalizeLayout" in js
    assert "renderLayoutPage" in js
    assert "n3-layout-sidebar-toggle" in js
    assert "n3-layout-sidebar-drawer" in js

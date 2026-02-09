from pathlib import Path


def test_navigation_renderer_contract() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    for marker in [
        'actionType === "open_page"',
        'actionType === "go_back"',
        "window.history.pushState",
        "__n3PagePopstateHandler",
        "n3-navigation-sidebar",
        "n3-navigation-item",
    ]:
        assert marker in js


def test_navigation_render_helpers_exist() -> None:
    navigation_helpers = Path("src/namel3ss/studio/web/render/navigation.tsx").read_text(encoding="utf-8")
    assert "normalizeNavigationItems" in navigation_helpers
    assert "findActiveNavigationTarget" in navigation_helpers
    page_switch = Path("src/namel3ss/studio/web/render/page_switch.tsx").read_text(encoding="utf-8")
    assert "resolvePageSlug" in page_switch
    assert "selectInitialPage" in page_switch

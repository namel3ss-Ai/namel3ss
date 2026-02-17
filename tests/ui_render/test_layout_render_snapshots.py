from pathlib import Path


def test_layout_renderer_supports_layout_nodes() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    for marker in [
        'el.type === "layout.stack"',
        'el.type === "layout.row"',
        'el.type === "layout.col"',
        'el.type === "layout.grid"',
        'el.type === "layout.sidebar"',
        'el.type === "layout.drawer"',
        'el.type === "layout.sticky"',
        'el.type === "conditional.if"',
        "body.dataset.hasSidebar = hasSidebar ? \"true\" : \"false\"",
        "body.dataset.hasDrawer = hasDrawer ? \"true\" : \"false\"",
        "applyLayoutSizingOptions(body, page);",
        "body.style.setProperty(\"--n3-layout-panel-max-height\"",
        "n3-layout-resize-handle",
        "attachResizeBehavior",
    ]:
        assert marker in renderer


def test_layout_tokens_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/styles/layout_tokens.css").read_text(encoding="utf-8")
    for selector in [
        ".n3-layout-stack",
        ".n3-layout-row",
        ".n3-layout-col",
        ".n3-layout-grid",
        ".n3-layout-sidebar",
        ".n3-layout-drawer",
        ".n3-layout-sticky",
    ]:
        assert selector in css


def test_layout_body_grid_contract_for_sidebar_and_drawer() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        '.n3-layout-body[data-has-sidebar="true"]',
        '.n3-layout-body[data-has-sidebar="false"][data-has-drawer="true"]',
        '.n3-layout-body[data-has-sidebar="true"][data-has-drawer="true"]',
    ]:
        assert selector in css


def test_layout_tokens_css_is_linked() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/styles/layout_tokens.css" in html

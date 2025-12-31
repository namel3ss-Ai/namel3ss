import re
from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_studio_guardrail_layout_invariants():
    html = _read("src/namel3ss/studio/web/index.html")
    html_lower = html.lower()

    assert 'data-testid="studio-preview"' in html
    assert 'data-testid="studio-preview-canvas"' in html
    assert 'data-testid="studio-dock"' in html
    assert html.find('data-testid="studio-preview"') < html.find('data-testid="studio-dock"')
    assert "pageSelect" not in html
    assert "preview-header" not in html
    assert "preview-controls" not in html

    for forbidden in ["sidebar", "inspector", "left-pane", "right-pane"]:
        assert forbidden not in html_lower

    dock_items = re.findall(r'data-testid="studio-dock-item-[^"]+"', html)
    assert len(dock_items) == 4
    for label in ["Graph", "Traces", "Memory", "Why"]:
        assert label in html

    assert 'data-testid="studio-sheet"' in html
    assert 'data-testid="studio-backdrop"' in html
    assert 'class="sheet hidden"' in html
    assert 'class="sheet-backdrop hidden"' in html


def test_studio_guardrail_topbar_invariants():
    html = _read("src/namel3ss/studio/web/index.html")
    html_lower = html.lower()

    assert 'data-testid="studio-topbar"' in html
    assert "namel3ss studio" in html_lower
    assert 'data-testid="studio-run-button"' in html
    assert "Run ▸" in html
    assert html.count('class="btn primary') == 1

    for forbidden in [
        "Settings",
        "Theme",
        "Registry",
        "Packages",
        "Security",
        "Editor",
        "Fix",
        "Auto-bind",
        "Tool wizard",
    ]:
        assert forbidden not in html


def test_studio_guardrail_behavior_invariants():
    tabs_js = _read("src/namel3ss/studio/web/app/setup/tabs.js")
    styles = _read("src/namel3ss/studio/web/styles.css")

    assert "backdrop.addEventListener" in tabs_js
    assert "event.key === \"Escape\"" in tabs_js
    assert "setActive(null)" in tabs_js
    assert ".sheet .panel-body" in styles
    assert "overflow: auto" in styles

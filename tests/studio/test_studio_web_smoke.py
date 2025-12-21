from pathlib import Path


def test_studio_html_structure():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "Namel3ss Studio" in html
    for label in ["Summary", "State", "Actions", "Traces", "Lint Findings", "UI Preview"]:
        assert label in html
    assert 'id="traces"' in html
    assert 'id="tracesFilter"' in html
    assert "Filter traces…" in html
    assert 'id="addElementButton"' in html
    assert 'id="inspectorBody"' in html
    renderer_js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    for token in ['el.type === "section"', 'el.type === "card"', 'el.type === "row"', 'el.type === "column"', 'el.type === "divider"', 'el.type === "image"']:
        assert token in renderer_js

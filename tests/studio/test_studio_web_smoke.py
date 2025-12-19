from pathlib import Path


def test_studio_html_structure():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "Namel3ss Studio" in html
    for label in ["Summary", "State", "Actions", "Traces", "Lint Findings", "UI Preview"]:
        assert label in html
    assert 'id="traces"' in html
    assert 'id="tracesFilter"' in html
    assert "Filter traces…" in html

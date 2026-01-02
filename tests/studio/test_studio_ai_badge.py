from pathlib import Path


def test_studio_ai_badge_markup_and_logic():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert 'id="aiModeBadge"' in html
    assert 'id="aiModeBadgeSetup"' in html
    assert "Open Setup" in html

    js = Path("src/namel3ss/studio/web/studio/setup.js").read_text(encoding="utf-8")
    assert "updateAiBadge" in js
    assert "aiModeBadgeSetup" in js
    assert 'classList.toggle("hidden"' in js

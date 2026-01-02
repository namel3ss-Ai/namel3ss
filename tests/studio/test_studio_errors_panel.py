from pathlib import Path


def test_studio_errors_panel_structure():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert 'id="errors"' in html
    assert 'id="errorBanner"' in html
    assert 'data-testid="studio-error-banner"' in html
    assert 'data-testid="studio-dock-item-errors"' in html


def test_studio_errors_panel_behavior():
    js = Path("src/namel3ss/studio/web/studio/errors.js").read_text(encoding="utf-8")
    assert "ai_provider_error" in js
    assert "Last run error" in js
    assert "Copy error JSON" in js
    assert "Copy diagnostics JSON" in js
    assert "Copy fix steps" in js
    assert "Open Setup" in js
    assert "Open Traces" in js
    assert "Fix steps" in js
    assert "What happened" in js
    assert "openTab(\"errors\")" in js
    assert "Bearer" in js
    assert "sk-" in js
    assert "fix-steps" in js
    assert 'replaceAll("\\\\n", "\\n")' in js
    assert "normalizeLineBreaks(buildFixSteps" in js

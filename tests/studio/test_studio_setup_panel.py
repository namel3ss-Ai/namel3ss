from pathlib import Path


def test_studio_setup_panel_smoke():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert 'data-testid="studio-dock-item-setup"' in html
    assert 'id="setup"' in html
    assert 'id="setupBanner"' in html
    assert 'id="secretsModal"' in html

    js = Path("src/namel3ss/studio/web/studio/setup.js").read_text(encoding="utf-8")
    assert "Missing secrets:" in js
    assert "sanitizeSecretName" in js
    assert "looksLikeSecretValue" in js
    assert "sk-" in js
    assert "length >= 40" in js
    assert "cp .env.example .env" in js
    assert "n3 secrets status --json" in js
    keys_js = Path("src/namel3ss/studio/web/studio/secret_keys.js").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in keys_js
    assert "GOOGLE_API_KEY" in keys_js

from pathlib import Path


def test_secret_keys_mapping():
    js = Path("src/namel3ss/studio/web/studio/secret_keys.js").read_text(encoding="utf-8")
    for token in [
        "NAMEL3SS_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "NAMEL3SS_ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEY",
        "NAMEL3SS_GEMINI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "NAMEL3SS_MISTRAL_API_KEY",
        "MISTRAL_API_KEY",
    ]:
        assert token in js


def test_secret_keys_expansion_helper():
    js = Path("src/namel3ss/studio/web/studio/secret_keys.js").read_text(encoding="utf-8")
    assert "expandPlaceholders" in js
    assert "<CANONICAL_KEY>" in js
    assert "<ALIAS_KEY>" in js
    assert "if (!keys) return text" in js
    assert "replace(/<CANONICAL_KEY>/g" in js
    assert "replace(/<ALIAS_KEY>/g" in js


def test_secret_keys_used_in_studio_panels():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/studio/secret_keys.js" in html

    errors_js = Path("src/namel3ss/studio/web/studio/errors.js").read_text(encoding="utf-8")
    traces_js = Path("src/namel3ss/studio/web/studio/traces.js").read_text(encoding="utf-8")
    setup_js = Path("src/namel3ss/studio/web/studio/setup.js").read_text(encoding="utf-8")

    for js in (errors_js, traces_js, setup_js):
        assert "expandPlaceholders" in js
        assert "<CANONICAL_KEY>" in js
        assert "<ALIAS_KEY>" in js

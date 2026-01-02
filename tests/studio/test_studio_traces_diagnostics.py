from pathlib import Path


def test_traces_diagnostics_copy_controls():
    js = Path("src/namel3ss/studio/web/studio/traces.js").read_text(encoding="utf-8")
    assert "Copy diagnostics JSON" in js
    assert "Copy fix steps" in js
    assert "ai_provider_error" in js
    assert "Bearer" in js
    assert "sk-" in js

    keys_js = Path("src/namel3ss/studio/web/studio/secret_keys.js").read_text(encoding="utf-8")
    assert "NAMEL3SS_OPENAI_API_KEY" in keys_js
    assert "OPENAI_API_KEY" in keys_js

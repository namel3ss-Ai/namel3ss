from pathlib import Path


def test_composer_payload_includes_message():
    js = Path("src/namel3ss/studio/web/ui_renderer_chat.js").read_text(encoding="utf-8")
    assert "normalizeComposerFields" in js
    assert 'name === "message"' in js
    assert "payload[name]" in js

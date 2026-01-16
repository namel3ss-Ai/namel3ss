from namel3ss.runtime.dev_server import BrowserAppState


def test_dev_server_recovers_after_fix(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\npage "home":\n  text is\n', encoding="utf-8")
    state = BrowserAppState(app, mode="dev", debug=False)
    status = state.status_payload()
    assert status.get("ok") is False
    overlay = status.get("overlay") or {}
    assert overlay.get("title") == "something went wrong"
    app.write_text('spec is "1.0"\n\npage "home":\n  text is "Hello"\n', encoding="utf-8")
    status = state.status_payload()
    assert status.get("ok") is True
    assert status.get("revision")
    manifest = state.manifest_payload()
    assert manifest["pages"][0]["name"] == "home"


def test_preview_manifest_includes_missing_media_placeholder(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\npage "home":\n  image is "welcome"\n', encoding="utf-8")
    state = BrowserAppState(app, mode="preview", debug=False)
    manifest = state.manifest_payload()
    image = manifest["pages"][0]["elements"][0]
    assert image["missing"] is True
    assert "fix_hint" in image


def test_preview_enforces_identity_runtime_rules(tmp_path):
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        'page "home": requires identity.role is "admin"\n'
        '  text is "Hi"\n',
        encoding="utf-8",
    )
    state = BrowserAppState(app, mode="preview", debug=False)
    payload = state.manifest_payload()
    assert payload.get("ok") is False
    entry = payload.get("error_entry") or {}
    assert "Identity is missing 'role'." in entry.get("message", "")

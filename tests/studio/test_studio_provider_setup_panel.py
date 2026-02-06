from pathlib import Path


def test_provider_setup_panel_wires_providers_api():
    js = Path("src/namel3ss/studio/web/studio/provider_setup.js").read_text(encoding="utf-8")
    assert "/api/providers" in js
    assert "Save provider settings" in js
    assert "Provider packs" in js
    assert "default_model" in js
    assert "secret_name" in js


def test_setup_panel_calls_provider_setup_module():
    js = Path("src/namel3ss/studio/web/studio/setup.js").read_text(encoding="utf-8")
    assert "providerSetup" in js
    assert "refreshProviders" in js
    assert "renderProviders" in js

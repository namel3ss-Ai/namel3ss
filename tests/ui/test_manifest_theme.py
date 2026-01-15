from tests.conftest import lower_ir_program


def test_manifest_includes_theme():
    source = 'app:\n  theme is "light"\n  theme_tokens:\n    accent is "secondary"\npage "home":\n  title is "Hi"\n'
    program = lower_ir_program(source)
    from namel3ss.ui.manifest import build_manifest
    data = build_manifest(program, state={}, store=None)
    theme = data.get("theme", {})
    assert theme.get("setting") == "light"
    assert theme.get("current") == "light"
    assert theme.get("runtime_supported") is False
    assert theme.get("tokens", {}).get("accent") == "secondary"


def test_manifest_reflects_runtime_theme():
    source = 'spec is "1.0"\n\nflow "demo":\n  set theme to "dark"\n'
    program = lower_ir_program(source)
    from namel3ss.ui.manifest import build_manifest
    data = build_manifest(program, state={}, store=None, runtime_theme="dark")
    theme = data.get("theme", {})
    assert theme.get("current") == "dark"
    assert theme.get("setting") == "light"
    assert theme.get("runtime_supported") is True
    assert theme.get("preference", {}).get("persist") == "none"

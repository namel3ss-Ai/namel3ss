from namel3ss.lint.engine import lint_source


def test_invalid_persist_value_reports():
    source = 'app:\n  theme is "system"\n  theme_preference:\n    persist is "disk"\n'
    findings = lint_source(source)
    assert any(f.code == "app.invalid_theme_persist" for f in findings)


def test_theme_change_disallowed():
    source = 'app:\n  theme is "system"\nflow "demo":\n  set theme to "dark"\n'
    findings = lint_source(source)
    assert any(f.code == "app.theme_override_disabled" for f in findings)

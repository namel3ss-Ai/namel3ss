from namel3ss.lint.engine import lint_source


SOURCE = '''record "User":
  name string

spec is "1.0"

flow "demo":
  save User
'''


def test_legacy_save_emits_warning():
    findings = lint_source(SOURCE)
    assert any(f.code == "N3LINT_SAVE_LEGACY" and f.severity == "warning" for f in findings)

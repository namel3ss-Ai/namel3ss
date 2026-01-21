from namel3ss.lint.engine import lint_source


def _finding_codes(findings):
    return [f.code for f in findings]


def test_alias_types_warn_with_replacement_message():
    src = '''spec is "1.0"

record "User":
  fields:
    age is int
'''
    findings = lint_source(src)
    assert "N3LINT_TYPE_NON_CANONICAL" in _finding_codes(findings)
    msg = findings[0].message
    assert "Use `number` instead of `int`" in msg
    assert findings[0].severity == "error"


def test_strict_mode_escalates_alias_to_error():
    src = '''spec is "1.0"

record "User":
  fields:
    name is string
'''
    findings = lint_source(src, strict=True)
    assert "N3LINT_TYPE_NON_CANONICAL" in _finding_codes(findings)
    assert any(f.severity == "error" for f in findings if f.code == "N3LINT_TYPE_NON_CANONICAL")


def test_canonical_types_do_not_warn():
    src = '''spec is "1.0"

record "User":
  fields:
    name is text
'''
    findings = lint_source(src)
    assert not findings


def test_relaxed_mode_downgrades_alias():
    src = '''spec is "1.0"

record "User":
  fields:
    age is int
'''
    findings = lint_source(src, strict=False)
    assert "N3LINT_TYPE_NON_CANONICAL" in _finding_codes(findings)
    assert any(f.severity == "warning" for f in findings if f.code == "N3LINT_TYPE_NON_CANONICAL")

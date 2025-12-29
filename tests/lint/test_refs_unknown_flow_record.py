from namel3ss.lint.engine import lint_source


def test_unknown_flow_and_record():
    source = '''spec is "1.0"

record "User":
  name string

page "home":
  button "Run":
    calls flow "missing"
  form is "Missing"
'''
    findings = lint_source(source)
    codes = [f.code for f in findings]
    assert "refs.unknown_flow" in codes
    assert "refs.unknown_record" in codes

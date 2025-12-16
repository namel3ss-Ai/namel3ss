from namel3ss.lint.engine import lint_source


def test_page_imperative_not_allowed_text_scan():
    source = 'page "home":\n  let x is 1\n'
    findings = lint_source(source)
    assert any(f.code == "page.imperative_not_allowed" for f in findings)

from namel3ss.lint.text_scan import scan_text


def test_detects_legacy_decl_and_one_line_button():
    lines = [
        'flow is "bad"',
        'button "Run" calls flow "demo"',
    ]
    findings = scan_text(lines)
    codes = [f.code for f in findings]
    assert "grammar.decl_uses_is" in codes
    assert "ui.button_one_line_forbidden" in codes

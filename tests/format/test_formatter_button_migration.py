from namel3ss.format.formatter import format_source


def test_button_migrates_to_block():
    source = 'spec is "1.0"\n\npage "home":\n  button "Run" calls flow "demo"\n'
    formatted = format_source(source)
    assert formatted == 'spec is "1.0"\n\npage "home":\n  button "Run":\n    calls flow "demo"\n'
